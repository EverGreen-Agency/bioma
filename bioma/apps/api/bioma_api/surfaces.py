"""Catálogo das superfícies navegáveis do Bioma e a resolução de acesso a elas.

Decisão 11 (2026-08-06): acesso e visibilidade em quatro níveis. Este módulo é
o lugar onde os quatro se encontram — e onde a pergunta "por que eu não vejo o
RH?" ganha resposta em vez de virar chamado de suporte.

**Superfície ≠ feature flag ≠ módulo.** São eixos ortogonais e misturá-los foi
o erro que esta decisão desfaz:

| Eixo | Pergunta | Onde mora |
|---|---|---|
| módulo (`enabled_modules`) | o cliente contratou? | `organizations` |
| feature flag | isto está pronto para este cliente? | `feature_flags.py` + `organization_feature_flags` |
| **superfície (aqui)** | esta pessoa/equipe deve enxergar esta tela? | este arquivo + `surface_grants` |
| preferência | eu quero ver isto agora? | `surface_preferences` |

**A chave da superfície é a rota.** `eg-rh` é `/eg-rh`; `operacao.radar-local` é
`/operacao/radar-local`. Não é estética: é o que permite partir de uma URL e
chegar ao motivo pelo qual ela sumiu do menu. Por isso as chaves de topo
repetem os `ViewId` que o frontend já usa (em português, fora da convenção de
chaves em inglês) — reaproveitar um identificador existente vale mais que abrir
um segundo vocabulário para a mesma coisa.

O catálogo vive em CÓDIGO, como o de feature flags: uma superfície existe
porque uma rota existe, e as duas devem nascer e morrer no mesmo commit. O
banco guarda só as exceções.
"""

from typing import Literal

Scope = Literal["eg", "client", "both"]

# `locked`: superfície que ninguém pode esconder de si mesmo. Sem isso, uma
# preferência mal clicada tranca a pessoa fora da própria home e a única saída
# é o banco.
SURFACE_CATALOG: dict[str, dict] = {
    # ---------------------------------------------------------------- topo EG
    "cockpit": {
        "label": "Cockpit",
        "group": "Principal",
        "scope": "eg",
        "locked": True,
    },
    "operacao": {
        "label": "Operação EG",
        "group": "Principal",
        "scope": "eg",
    },
    "clientes": {
        "label": "Carteira de Clientes",
        "group": "Principal",
        "scope": "both",
        # Para o usuário de cliente esta é a home ("Meu Hub") — esconder seria
        # deixá-lo sem lugar nenhum para pousar.
        "locked": True,
    },
    "engenharia": {
        "label": "Engenharia",
        "group": "Operação EG",
        "scope": "eg",
    },
    # O copiloto não é uma rota — é um painel lateral que acompanha todas as
    # telas. Entra no catálogo mesmo assim porque a pergunta que o usuário faz
    # é a mesma ("não quero ver isso agora"), e deixá-lo de fora obrigaria uma
    # segunda configuração num segundo lugar para o mesmo tipo de decisão.
    "copiloto": {
        "label": "Copiloto",
        "group": "Assistente",
        "scope": "eg",
        "feature_key": "copilot",
    },
    "eg-wiki": {"label": "Wiki EG", "group": "Operação EG", "scope": "eg"},
    "eg-ideas": {"label": "Banco de Ideias", "group": "Operação EG", "scope": "eg"},
    "eg-tech": {"label": "Banco de Stack", "group": "Operação EG", "scope": "eg"},
    "eg-architecture": {"label": "Arquitetura", "group": "Operação EG", "scope": "eg"},
    "eg-rh": {"label": "Gestão RH", "group": "Operação EG", "scope": "eg"},
    "eg-kits": {"label": "Logística Kits", "group": "Operação EG", "scope": "eg"},
    "eg-propostas": {"label": "Freelas e Propostas", "group": "Operação EG", "scope": "eg"},
    "eg-planning": {"label": "Planejamentos", "group": "Operação EG", "scope": "eg"},
    "eg-plataformas": {"label": "Estudo de Plataformas", "group": "Operação EG", "scope": "eg"},
    "eg-vitorias": {"label": "Mural de Vitórias", "group": "Operação EG", "scope": "eg"},
    "sales_copilot": {
        "label": "Copiloto de Vendas",
        "group": "Operação EG",
        "scope": "eg",
        "module": "commercial",
        "feature_key": "sales_copilot",
    },
    # -------------------------------------------- sub-rotas de /operacao (EG)
    "operacao.tarefas": {
        "label": "Tarefas da EG",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
    },
    "operacao.crm": {
        "label": "CRM da EG",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
        "module": "commercial",
    },
    "operacao.financeiro": {
        "label": "Financeiro da EG",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
        "module": "finance",
    },
    "operacao.metricas": {
        "label": "Métricas da EG",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
        "module": "analytics",
    },
    "operacao.ia": {
        "label": "Operações IA",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
    },
    "operacao.pesquisa-mercado": {
        "label": "Pesquisa de mercado",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
    },
    "operacao.prova": {
        "label": "Prova",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
    },
    "operacao.radar-local": {
        "label": "Radar Local",
        "group": "Operação EG",
        "scope": "eg",
        "parent": "operacao",
        "feature_key": "local_radar",
    },
    "whatsapp": {
        "label": "WhatsApp & Disparos",
        "group": "Operação EG",
        "scope": "both",
        "module": "integrations",
        "feature_key": "whatsapp-multiprovider",
    },
    # ------------------------------------------------ hub do cliente (ambos)
    "cliente.hub": {
        "label": "Visão geral do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "hub",
        "locked": True,
    },
    "cliente.contexto": {
        "label": "Contexto do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "hub",
    },
    "cliente.projetos": {
        "label": "Projetos e contratos",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "hub",
    },
    "cliente.conteudo-ia": {
        "label": "Estúdio IA",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "content",
    },
    "cliente.crm": {
        "label": "CRM do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "commercial",
    },
    "cliente.financeiro": {
        "label": "Financeiro do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "finance",
    },
    "cliente.analytics": {
        "label": "Métricas do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "analytics",
    },
    "cliente.documentos": {
        "label": "Documentos do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "files",
    },
    "cliente.tarefas": {
        "label": "Tarefas do cliente",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "hub",
    },
    "cliente.acessos": {
        "label": "Acessos (cofre)",
        "group": "Hub do cliente",
        "scope": "both",
        "module": "hub",
    },
    "cliente.integracoes": {
        "label": "Integrações do cliente",
        "group": "Hub do cliente",
        "scope": "eg",
        "module": "integrations",
    },
}


def is_known(surface_key: str) -> bool:
    return surface_key in SURFACE_CATALOG


def entry(surface_key: str) -> dict:
    return SURFACE_CATALOG[surface_key]


def is_locked(surface_key: str) -> bool:
    return bool(SURFACE_CATALOG.get(surface_key, {}).get("locked"))


def module_of(surface_key: str) -> str | None:
    return SURFACE_CATALOG.get(surface_key, {}).get("module")


def feature_key_of(surface_key: str) -> str | None:
    return SURFACE_CATALOG.get(surface_key, {}).get("feature_key")


def parent_of(surface_key: str) -> str | None:
    return SURFACE_CATALOG.get(surface_key, {}).get("parent")


def keys_for_scope(is_eg: bool) -> list[str]:
    """Superfícies que fazem sentido para o tipo de usuário.

    Uma tela de cliente nunca deve aparecer na lista de preferências de quem é
    EG e vice-versa — oferecer para esconder algo que a pessoa jamais veria é
    ruído que faz a tela parecer quebrada.
    """
    wanted: tuple[str, ...] = ("eg", "both") if is_eg else ("client", "both")
    return [key for key, item in SURFACE_CATALOG.items() if item.get("scope", "both") in wanted]
