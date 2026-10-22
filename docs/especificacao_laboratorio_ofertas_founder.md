# Especificação Técnica: Laboratório de Ofertas e Metodologias Founder Skill

**Data:** 22 de Outubro de 2026  
**Status:** Implementado (Pronto para Produção)  
**Branch:** `feature/founder-methodology-integration`  
**Autores:** Engenharia de Software & Arquitetura Bioma  

---

## 1. Fundamentação Teórica e Motivação de Domínio

### 1.1 O Problema da Comoditização de Agências e Serviços B2B
No ecossistema de agências de crescimento e marketing digital, a falha mais comum no fechamento e retenção de contas corporativas é a **comoditização da oferta**: vender "horas de trabalho", "gestão de anúncios" ou "posts em redes sociais" em vez de resultados de negócios assimétricos. Quando uma agência compete por preço ou escopo de entrega bruto, a margem de lucro despenca e a retenção se fragiliza.

### 1.2 O Framework $100M Offers (Alex Hormozi)
Para romper o equilíbrio destrutivo da concorrência perfeita, adotamos a **Equação de Valor de Alex Hormozi**:

$$\text{Valor Percebido} = \frac{\text{Resultado dos Sonhos (Dream Outcome)} \times \text{Probabilidade Percebida (Perceived Likelihood)}}{\text{Tempo de Espera (Time Delay)} \times \text{Esforço e Sacrifício (Effort \& Sacrifice)}}$$

* **Numerador (Maximização):**
  * *Dream Outcome:* O estado transformacional desejado (receita incremental, autoridade, autonomia).
  * *Perceived Likelihood:* Confiança racional e emocional de que o método realmente funcionará para o cliente (provas sociais concretas, histórico demonstrável, processo claro).
* **Denominador (Minimização para zero):**
  * *Time Delay:* Tempo decorrido entre o investimento e o primeiro retorno perceptível (*Time to First Value / Quick Wins*).
  * *Effort & Sacrifice:* O atrito cognitivo e operacional que o cliente precisa suportar. Reduzido ao migrar de "Faça Você Mesmo" (DIY) para "Feito Para Você" (DFY).

### 1.3 O Framework Zero to One (Peter Thiel) e o Conselho Virtual
Peter Thiel estabelece que o objetivo de uma empresa sustentável é criar um **monopólio criativo** baseado em vantagens 10x superiores (tecnologia proprietária, efeitos de rede, economias de escala e marca).
Integramos a sabatina de conselho consultivo com 3 personas críticas:
1. **Alex Hormozi:** Foco na matemática da oferta, reversão de risco (garantias condicionais/incondicionais), precificação assimétrica e empilhamento de bônus (*Grand Slam Offer Stack*).
2. **Steve Jobs:** Foco em simplicidade radical, poda de ruídos e obsessão pela experiência do cliente final.
3. **Peter Thiel:** Foco em barreira competitiva de longo prazo, pergunta contrariana e fuga da competição destrutiva.

---

## 2. Arquitetura de Software Implementada

Seguindo estritamente as diretrizes de **Clean Architecture** e **Domain-Driven Design (DDD)** do Bioma:

```
[ Frontend: React / TypeScript / TanStack Query ]
               │
               ▼ HTTP (REST / JSON)
[ Router: FastAPI (/offer-lab, /workspaces/{id}/offer-validations) ]
               │
               ▼ Injeção de Dependências
[ Service: OfferLabService (Cálculo Hormozi, Board Engine, Auditoria) ]
               │
               ▼ SQL Parametrizado (sem ORM pesado, sem mocks)
[ Repository: OfferLabRepository (PostgreSQL / JSONB) ]
               │
               ▼
[ Banco de Dados: Tabela workspace_offer_validations (Migration 0115) ]
```

### 2.1 Banco de Dados (Migration 0115)
- **Tabela:** `workspace_offer_validations`
- **Chave Primária:** UUID (`gen_random_uuid()`)
- **Isolamento Multi-tenant:** Coluna `workspace_id` com chave estrangeira para `client_workspaces(id)` e constraint `ON DELETE CASCADE`.
- **Campos JSONB Estruturados:**
  - `value_equation`: Objeto com as 4 dimensões (1 a 10) e o `value_score` normalizado (0 a 100).
  - `problems_and_solutions`: Array de mapeamento dor $\to$ solução $\to$ veículo de entrega.
  - `offer_stack`: Objeto com core, array de bônus, garantia de reversão de risco e gatilho de escassez/urgência.
  - `board_verdict`: Vereditos individuais de Hormozi, Jobs e Thiel, veredito consolidado, dealbreakers e plano de ação imediato.
- **Triggers de Auditoria:** `updated_at` automatizado via trigger PostgreSQL.

### 2.2 Camada de Domínio e Serviço (Python / FastAPI)
- **Schema Pydantic:** Validação rigorosa de tipos, restrições numéricas (`ge=1, le=10`) e defaults seguros em `apps/api/bioma_api/schemas/offer_lab.py`.
- **Serviço de Negócio:**
  - Cálculo determinístico com prevenção de divisão por zero:
    $$\text{raw} = \frac{\text{dream} \times \text{likelihood}}{\max(\text{time} \times \text{effort}, 1)}$$
    $$\text{normalized} = \min\left(100, \frac{\text{raw}}{100} \times 100\right)$$
  - Detecção algorítmica de **Dealbreakers**:
    - Se $Tempo > 7$: alerta crítico de demora no retorno.
    - Se $Esforço > 7$: alerta crítico de sobrecarga no cliente.
    - Se $Garantia$ ausente: risco de fricção no fechamento.
    - Se $Probabilidade < 5$: falta de prova social e confiança.
  - Veredito especializado gerado por persona de conselheiro.
  - Integração de log de auditoria com `client_hub_repo.write_audit` no momento da persistência.

### 2.3 Camada de Apresentação (React 19 / TypeScript / Vite)
- **Componente:** `OfferLabStudio` em `apps/web/src/components/offer-lab/OfferLabStudio.tsx`.
- **Design System:** Totalmente alinhado aos padrões visuais do Bioma (dark mode, cartões translúcidos com borda `border-[var(--color-border-subtle)]`, controles interativos de slider, badge de score com codificação de cor semafórica, sem mock data).
- **Roteamento:** Acesso sob `/operacao/validador-oferta` dentro do shell `AgencyWorkspaceView`, protegido por `guardSurface`.
- **Gerenciamento de Estado:** React Query (`useQuery`, `useMutation`) com invalidação automática de cache na persistência e exclusão.

---

## 3. Integração com Antigravity Copilot (Agent Skills)

Foram incorporadas 3 skills de pair programming no projeto:
1. `.agents/skills/founder-offer/SKILL.md` (e em `.agent/skills/skills/founder-offer/SKILL.md`): Instruções operacionais para formulação de ofertas Hormozi.
2. `.agents/skills/founder-board/SKILL.md`: Protocolo de sabatina "Grill Me" com os 3 conselheiros.
3. `.agents/skills/founder-zero-to-one/SKILL.md`: Framework de diferenciação e monopólio criativo de Thiel.

---

## 4. Testes e Validação de Qualidade

1. **Testes Unitários:** 4 testes implementados em `apps/api/tests/test_offer_lab.py`:
   - Cálculo da equação de valor com limites normalizados.
   - Detecção de dealbreakers por sobrecarga e tempo.
   - Síntese de avaliação com vereditos de conselho.
   - Avaliação com payload completo (problemas, bônus, garantia).
   - **Resultado:** `4 passed in 0.52s`.
2. **Compilação e Tipagem:**
   - Python: `python -m compileall bioma_api` $\to$ 0 erros.
   - Frontend: `npx tsc -b && vite build` $\to$ 0 erros de compilação, bundle gerado em 13.85s.
3. **Smoke Test Operacional:** `apps/api/scripts/smoke_offer_lab.py` executado com sucesso validando o ciclo de vida completo da API.
