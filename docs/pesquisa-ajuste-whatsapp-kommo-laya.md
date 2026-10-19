# Diagnóstico Técnico: Alinhamento de Funil WhatsApp, Sincronização Kommo e Laya AI

**Data:** 19/10/2026  
**Contexto:** Univet Loupes CRM (Kommo) & Portal Bioma EG  
**Fontes Primárias:**
- Código e endpoints: [`apps/api/bioma_api/services/kommo_portal.py`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/bioma_api/services/kommo_portal.py), [`lead_classifier.py`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/bioma_api/lead_classifier.py), [`config.py`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/api/bioma_api/config.py)
- Frontend: [`apps/web/src/views/univet/UnivetEgPortal.tsx`](file:///c:/Users/Lenovo/Desktop/EG/bioma/apps/web/src/views/univet/UnivetEgPortal.tsx)
- Documentação canônica: [`docs/univet-loupes-context.md`](file:///c:/Users/Lenovo/Desktop/EG/bioma/docs/univet-loupes-context.md), [`docs/univet-conexoes-passo-a-passo.md`](file:///c:/Users/Lenovo/Desktop/EG/bioma/docs/univet-conexoes-passo-a-passo.md)

---

## 1. Onde Paramos (Portais Paralelos & Apresentação)

A estrutura atual conta com três ambientes complementares:
1. **`/portal/univet` (Demo Executiva / Reunião):**
   - Dados demonstrativos consistentes (`apps/web/src/data/univet/univetPortalData.ts`).
   - Apresenta o fluxo completo para o cliente: aquisição, mapa de representantes por UF, faturamento cruzado Nomus e funil de conversão.
   - Material de apoio preparado: [`docs/looker-studio-univet-guia-reuniao.md`](file:///c:/Users/Lenovo/Desktop/EG/bioma/docs/looker-studio-univet-guia-reuniao.md) e sementes em `apps/api/seed_data/looker_mock/`.
2. **`/portal/univet/v2` (Painel com Dados Reais):**
   - Público, sem login; consome agregados de `kommo_crm_snapshots` sem expor dados pessoais (LGPD).
3. **`/portal/univet/eg` (Operação Interna EverGreen):**
   - Conexão e sincronização do Kommo, varredura de duplicatas de contatos e motor Laya AI em tempo real via Webhook.

---

## 2. Diagnóstico da Divergência: Negócios (Leads) = 1 vs. Contatos = 38

| Métrica no Painel | Valor Exibido | Origem do Dado | Causa da Divergência |
|---|:---:|---|---|
| **Contatos analisados** | 38 | Chamada direta da varredura (`/api/v4/contacts`) | O botão "Rodar varredura" fez consulta ao vivo na API do Kommo e leu os 38 contatos recentes. |
| **Negócios (Leads)** | 1 | Tabela `kommo_crm_snapshots` no PostgreSQL | A métrica é alimentada apenas quando o botão **"Sincronizar leads"** é acionado. Como o CRM foi zerado e os novos 38 leads chegaram depois da última sincronização, o snapshot no banco ainda refletia o estado anterior (1 lead). |

**Ação:** Clicar em **"Sincronizar leads"** no portal `/portal/univet/eg`. A API buscará `/api/v4/leads` e atualizará o snapshot para 38.

---

## 3. Diagnóstico do Erro Laya AI

**Mensagem retornada nos cards:**
```json
{"detail":"unknown model 'english,multilingual'; use laya-auto (or a TypeSafe name such as jev-latest) or one of laya-english, laya-multilingual"}
```

### Causa Raiz
- Na configuração de ambiente da API (Railway / `.env`), a variável `DECISION_MODEL_NAME` foi definida como `english,multilingual`.
- A API do modelo TypeSafe/Laya (`https://api.typesafe.ai/v1/systemone`) espera uma string unitária de identificador de modelo:
  - `laya-multilingual` (recomendado para conversas de WhatsApp em português);
  - `laya-auto`;
  - ou `jev-latest`.

### Impacto
- Cada webhook disparado pelo Kommo (`add_message` ou `add_lead`) chamou `ask_decision_model` com o nome inválido, resultando em erro HTTP 400/422 e persistindo o registro com status `erro` em `kommo_lead_classifications`.

### Correção
1. Alterar no Railway: `DECISION_MODEL_NAME=laya-multilingual`.
2. No portal EG, clicar em **"Limpar registros de teste"** (`/portal-api/univet/eg/classification/reset`) para descartar o histórico com falha.

---

## 4. Conexão do WhatsApp no Pipeline e Procedimento de Ajuste

### Diagnóstico do Funil
Na listagem do Kommo:
- **Funil atual:** `Funil de vendas`
- **Etapa:** `Leads de entrada`

### O que fazer? (Procedimento Recomendado)
O procedimento nativo em duas etapas é o mais seguro e recomendado, pois preserva todas as conversas, anexos, números de telefone e IDs dos leads:

1. **Ajustar o Conector de WhatsApp (Novos Leads):**
   - No Kommo, acesse **Configurações → Comunicação / Integrações** (canal WhatsApp / WppConnect / Kommo Chat).
   - Localize a configuração de criação automática de leads e altere o **Funil de destino** para o funil correto da Univet (ex.: funil oficial de Vendas/Comercial) e a **Etapa inicial** para a etapa de triagem desejada (ex.: "Leads de entrada" ou "01 Primeiro atendimento").
   - Salve. Novos atendimentos entrarão automaticamente no destino certo.

2. **Mover os 38 Leads Existentes em Massa (Kommo UI):**
   - Na tela "TODOS OS LEADS" do Kommo (conforme print 3):
   - Marque a caixa de seleção superior (ao lado da coluna `LEAD TÍTULO`) para selecionar todos os 38 registros.
   - Na barra de ação em massa que surge no rodapé, selecione **"Alterar etapa"** (ou "Mover funil").
   - Aponte para o Funil correto e para a Etapa correspondente.
   - Confirme a alteração. O Kommo transfere os cards mantendo intactos todos os históricos de chat do WhatsApp e contatos vinculados.

3. **Atualização e Reclassificação no Bioma:**
   - Acesse `/portal/univet/eg`.
   - Clique em **"Sincronizar leads"** para atualizar o snapshot e os funis.
   - Clique em **"Limpar registros de teste"** para eliminar as falhas anteriores do Laya.
   - O webhook e o classificador passarão a processar e preencher automaticamente os campos clínicos dos 38 leads.
