# Pesquisa Técnica: Arquitetura de Integração Kommo CRM + Nomus ERP + n8n (Univet Loupes)

**Data:** 15/09/2026  
**Contexto:** Univet Loupes (Sistemas Ópticos & Lupas de Alta Precisão) / EverGreen Agency (Bioma Platform)  
**Objetivo:** Especificação técnica e levantamento de arquitetura para ingestão de leads, deduplicação de contatos no Kommo CRM, orquestração via n8n e sincronização bidirecional com o Nomus ERP.

---

## 1. Kommo CRM: Arquitetura de Contatos, Leads e Deduplicação

### 1.1. Modelo de Dados (API v4)
No Kommo (antigo amoCRM), os objetos principais do funil comercial são:
- **Leads (`/api/v4/leads`)**: Representam o negócio/oportunidade em um pipeline (`pipeline_id`, `status_id`, `price`).
- **Contacts (`/api/v4/contacts`)**: Representam as pessoas físicas (`name`, `custom_fields_values` contendo telefone, e-mail, especialidade médica/odonto, etc.). Um lead pode ter um ou mais contatos vinculados via `_embedded.contacts`.
- **Companies (`/api/v4/companies`)**: Representam a clínica/hospital/PJ associada.

### 1.2. O Problema das Duplicatas no Kommo
O Kommo permite criar contatos idênticos se a criação for feita via chamadas isoladas na API de contatos sem verificação prévia (`POST /api/v4/contacts`).
Causas frequentes:
1. **Múltiplos pontos de entrada**: Formulário do site, clique/conversa no WhatsApp (via Blip/SleekFlow/Z-API), campanhas de tráfego (Meta Lead Ads / Google Ads).
2. **Re-engajamento do mesmo lead**: O médico/dentista que já converteu antes preenche novamente um formulário solicitando demonstração ou novo produto.
3. **Formatação heterogênea**: Telefones cadastrados com ou sem DDD, com ou sem nono dígito, com `+55`, com espaços ou traços (`(11) 98765-4321` vs `5511987654321`).

### 1.3. Mecanismos Nativos vs. Customizados de Deduplicação
1. **Duplicate Control Nativo (Automate Pipeline)**:
   - O Kommo possui um recurso nativo em **Pipelines → Automate → Duplicate control** que unifica leads vindos de canais de chat conectados (WhatsApp, Instagram, etc.).
   - Na API, o endpoint `POST /api/v4/leads/complex` participa do Duplicate Control se ativado, sinalizando `merged: true` no retorno.
2. **Limitações do Nativo**:
   - Não possui endpoint REST público para "merge arbitrário" de dois IDs de contato já criados.
   - Não resolve variações sutis de telefone sem sanitização prévia (ex: DDD com ou sem zero, ausência do DDI 55).
3. **Estratégia Recomendada para o Bioma/n8n**:
   - **Ingestão com Pre-Check (Padrão Get-or-Create com Upsert)**:
     - Sanitizar telefone para o formato canônico E.164 (ex: `+5511987654321`) e e-mail em lowercase.
     - Buscar contato existente: `GET /api/v4/contacts?query=+5511987654321`.
     - Se encontrado: reutiliza o `contact_id`, atualiza campos customizados (`PATCH /api/v4/contacts/{id}`) e cria a nova oportunidade vinculada a ele (`POST /api/v4/leads` com `_embedded.contacts = [{"id": contact_id}]`).
     - Se não encontrado: cria o contato e cria o lead em transação.
   - **Worker de Limpeza & Reconciliação Periódica**:
     - Varre contatos criados nas últimas 24h, agrupa por telefone/e-mail e reatribui leads órfãos ao contato canônico mais antigo antes de arquivar os duplicados.

---

## 2. Nomus ERP Industrial: Capacidades de Integração e API REST

### 2.1. Arquitetura da API do Nomus
- **Protocolo:** RESTful HTTP sobre JSON.
- **Padrão de URL:** `https://{nomus_host}/{contexto}/rest/{servico}`.
- **Autenticação:** HTTP Basic Authentication (`Authorization: Basic base64(chave_acesso)`). A chave é configurada em "Configuração Geral > Chave de acesso para integração com o erp via REST".
- **Header:** `Content-Type: application/json`.

### 2.2. Serviços e Entidades Relevantes para a Univet
1. **Clientes (`/rest/clientes`)**:
   - Criação ou atualização do cadastro do cirurgião/clínica (CPF/CNPJ, Inscrição Estadual, endereço de entrega das lupas, contato financeiro).
2. **Pedidos de Venda (`/rest/pedidos_venda`)**:
   - Criação do pedido formal quando o lead no Kommo chega ao estágio "Fechamento / Venda Ganha".
   - Dados obrigatórios: cliente, itens (modelo da lupa, magnificação, distância de trabalho, iluminação LED), condições de pagamento, representante comercial responsável.
3. **Status de Faturamento / NF-e (`/rest/notas_fiscais` / webhooks)**:
   - Consulta ou notificação de faturamento e emissão da NF-e para notificar o cliente e o representante, além de alimentar o retorno de ROI no Bioma.

### 2.3. Padrão de Gatilhos e Webhooks no Nomus
- O Nomus suporta webhooks para eventos específicos de clientes e pedidos (conforme módulos e conectores contratados).
- Caso o ambiente da Univet não possua webhook de saída ativo no Nomus, a sincronização do status de faturamento/pedido pode ser feita via **Polling agendado no Bioma Worker** (ex: a cada 30 minutos consulta pedidos com status pendente).

---

## 3. Papel do n8n vs. Bioma Platform (FastAPI + Worker)

### 3.1. Divisão de Responsabilidades
Para manter conformidade estrita com o `ARCHITECTURE.md` do Bioma e evitar acoplamentos frágeis:

| Camada | Ferramenta | Responsabilidade |
|---|---|---|
| **Ponto de Ingestão & Roteamento** | **n8n** | Receber webhooks do site Univet, Elementor, Typeform, campanhas e WhatsApp. Extrair UTMs, sanitizar payloads preliminares e orquestrar réguas de comunicação externa (notificações Slack/WhatsApp dos representantes). |
| **Normalização, Deduplicação & Regra de Negócio** | **Bioma API & Worker (`apps/api/bioma_api/integrations/kommo`)** | Implementar lógica transacional confiável: normalização E.164, busca e upsert de contatos no Kommo, histórico de auditoria (`audit_events`), persistência de snapshots e integração segura com Nomus ERP. |
| **Cockpit & FinOps / Analytics** | **Bioma Web (`apps/web`)** | Visualização do funil: Mídia Gasta → CPL → Reuniões Agendadas → Pedidos Nomus → Faturamento Líquido (R$). |

---

## 4. Próximos Passos de Validação (Grill-Me)
1. Definir isolamento de workspace/worktree para não colidir com o desenvolvimento paralelo na branch atual.
2. Homologar credenciais da API do Nomus (ambiente de teste/produção da Univet).
3. Configurar regras de unificação de duplicatas (prioridade por telefone celular vs e-mail vs CPF).
