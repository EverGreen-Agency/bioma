# Consciência cross-repo do Arquiteto (eg-scan)

**Id:** cross-repo-awareness
**Categoria:** Infra

## Problema
O Gate de Alavancagem do Arquiteto ("já construímos isso em algum projeto?") só vale se ele souber **quais projetos existem** e **onde estão** — sem o humano ficar mencionando um por um. E os projetos da EG (internos + de cliente) só crescem.

## Solução — duas fontes vivas + uma cola
1. **Descoberta ("que projetos existem"):** a org **EverGreen-Agency** no GitHub é a fonte viva (`gh repo list EverGreen-Agency`). Clientes em orgs separadas: some as orgs. Zero lista à mão.
2. **Local ("o que está clonado + indexado"):** escanear a pasta-raiz `Desktop/EG/` por repos git (`.git`) e ver quais têm `.codegraph/`.
3. **Cola (`eg-scan`):** um comando que lê a lista e roda a mesma pergunta do codegraph em **todos** os repos indexados (`codegraph explore -p <repo>`), devolvendo um **resumo combinado**. O humano pergunta uma vez; não gerencia caminhos.

## Decisão: codegraph POR REPO (não índice único)
Cada repo tem seu `.codegraph/`. Índice único sobre `Desktop/EG` poderia engolir `node_modules` de todos e ficar pesado. O "lugar central" é o **resumo do eg-scan**, não um banco fundido.

## Conexões
- **Depende de** `codegraph` (o motor de consulta).
- Alimenta o **Gate de Alavancagem** do Arquiteto e a avaliação da **mega plataforma** (comparar contra tudo que já fizemos).
- Pré-requisito de descoberta remota: `gh` instalado + `gh auth login`.
