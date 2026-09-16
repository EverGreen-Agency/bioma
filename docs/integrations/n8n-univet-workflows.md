# Especificação e Manual de Implantação dos Workflows n8n (Univet Loupes)

Este documento descreve os fluxos de trabalho configurados no n8n para a operação da **Univet Loupes**, abrangendo a sincronização bidirecional do Nomus ERP com o Kommo CRM, o gatekeeper de ingestão com pré-validação para evitar contatos duplicados e a alimentação do Cockpit de BI do Bioma.

---

## 1. Variáveis de Ambiente Necessárias no n8n

Configure as seguintes variáveis no painel do n8n (**Settings → Variables** ou `.env`):

| Variável | Descrição | Exemplo de Valor |
|---|---|---|
| `NOMUS_API_BASE_URL` | URL base da API REST do Nomus ERP | `https://univet.nomus.com.br/univet` |
| `NOMUS_AUTH_BASIC` | Chave de integração REST em Base64 | `Basic Q2hhdmVJbnRlZ3JhY2Fv...` |
| `KOMMO_BASE_URL` | Subdomínio da conta Kommo | `https://univet.kommo.com` |
| `KOMMO_ACCESS_TOKEN` | Token OAuth2 de longa duração / Bearer | `eyJ0eXAi...` |
| `KOMMO_STATUS_ID_VENDA_GANHA` | ID numérico do estágio 'Venda Ganha' | `142` |
| `BIOMA_API_BASE_URL` | URL base da API do Bioma | `https://api.bioma.evergreen.agency` |
| `UNIVET_WORKSPACE_ID` | UUID do workspace da Univet no Bioma | `00000000-0000-0000-0000-000000000000` |
| `BIOMA_INTEGRATION_TOKEN` | Token de serviço para envio de métricas | `bio_sec_...` |

---

## 2. Fluxo 1: Sincronização Nomus ERP → Kommo CRM (+ Bioma BI)

### Objetivo:
Como a equipe da Univet opera exclusivamente dentro do Nomus ERP no faturamento e expedição das lupas, este workflow consulta periodicamente pedidos aprovados/faturados e atualiza as oportunidades no Kommo CRM para garantir feedback de vendas e rastreamento de ROI.

### Passo a Passo dos Nós:
1. **Cron Nomus Polling (15m)**: Dispara a cada 15 minutos.
2. **Buscar Pedidos Faturados no Nomus**:
   - `GET /rest/pedidos_venda?status=FATURADO,APROVADO&data_modificacao_inicio={{$now.minus({minutes: 20}).toISO()}}`
   - Autenticado via Basic Auth.
3. **Sanitizar Dados do Pedido Nomus (Code Node)**:
   - Extrai e limpa CNPJ/CPF (somente dígitos).
   - Normaliza telefone para formato brasileiro (DDI 55 + DDD + número).
   - Normaliza e-mail (lowercase).
4. **Buscar Contato no Kommo**:
   - `GET /api/v4/contacts?query={{telefone || email || cpf}}&with=leads`
5. **Atualizar Lead no Kommo para Ganho**:
   - `PATCH /api/v4/leads/{{target_lead_id}}`
   - Atualiza `status_id` para o estágio de Venda Ganha e registra o valor final faturado.
6. **Notificar Bioma Cockpit (BI)**:
   - `POST /workspaces/{id}/integrations/sales_event`
   - Registra o evento de faturamento para cálculo automático de CAC, ROAS e faturamento do cliente Univet.

---

## 3. Fluxo 2: Ingestão de Leads com Pre-Check (Prevenção de Duplicatas)

### Objetivo:
Impedir que novos leads oriundos do site Univet ou conversas de WhatsApp gerem contatos duplicados no Kommo.

### Passo a Passo:
1. **Webhook Ingestão (Site / WhatsApp Univet)**: Endpoint HTTP público recebendo dados do formulário ou webhook do canal.
2. **Pre-Check Normalizer (Code Node)**:
   - Aplica a mesma regra de normalização de telefone E.164 (compatibilizando celulares de 8 e 9 dígitos).
3. **Verificar se Contato Já Existe**:
   - Consulta `/api/v4/contacts?query={{canonical_phone}}`.
   - Se o contato já existir:
     - **Não** cria novo contato.
     - Apenas adiciona um novo Lead vinculado ao `contact_id` existente.
   - Se não existir:
     - Cria o novo contato e em seguida o Lead.
