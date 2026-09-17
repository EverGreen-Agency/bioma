"""Resolução dos quatro níveis de acesso a uma superfície.

Função pura de propósito: recebe dados já lidos e devolve a decisão com o
motivo. Sem banco aqui — o que garante que a regra seja testável linha a linha
e que a explicação mostrada na tela venha do MESMO cálculo que nega a rota. Ter
duas implementações (uma que decide, outra que explica) é como se produz a
tela que jura que você tem acesso enquanto a API responde 403.

## A ordem, do mais forte para o mais fraco

1. **Teto da organização** — contratou o módulo? a feature está madura? Nada
   abaixo ultrapassa isto. É o único nível que vale como segurança para
   cliente.
2. **Equipe** — entre equipes, *o mais restritivo vence*: quem está em duas
   equipes e uma delas nega, não vê. Negar precisa ser suficiente sozinho,
   senão basta entrar numa equipe permissiva para furar a regra.
3. **Usuário** — vence a equipe, nos dois sentidos. Aqui a regra NÃO é "o mais
   restritivo": um `allow` de usuário devolve o que a equipe tirou.
4. **Preferência pessoal** — só esconde. Nunca concede.

## Sobre o nível 3 (a única interpretação que fiz)

A decisão 11 diz "o mais restritivo vence". Aplicada ao pé da letra entre
equipe e usuário, ela tornaria o nível de usuário inútil para o caso que o
motivou: negar o RH para a equipe inteira e liberar para a pessoa que cuida do
RH. Sem exceção por pessoa, a saída seria não negar para a equipe — e aí o
nível de equipe é que não serve para nada.

Então: **especificidade decide entre equipe e usuário; restritividade decide
dentro do mesmo nível; e o teto da organização não se fura por nenhum dos
dois.** A propriedade que a regra original protege — "esconder não vira jeito
acidental de burlar acesso" — continua valendo inteira, porque ela mora no
nível 1 e na preferência, não aqui.
"""

from dataclasses import dataclass, field
from typing import Literal

from bioma_api import surfaces

Reason = Literal[
    "locked",
    "platform_admin",
    "not_contracted",
    "maturity",
    "team_denied",
    "team_allowed",
    "user_denied",
    "user_allowed",
    "preference",
    "default",
]


@dataclass
class SurfaceGrant:
    """Uma exceção vinda do banco. `subject_label` é o nome que a tela mostra."""

    effect: Literal["allow", "deny"]
    subject_label: str
    note: str | None = None


@dataclass
class SurfaceAccess:
    surface_key: str
    label: str
    group: str
    parent: str | None
    locked: bool
    # Permissão: o backend deixa entrar? É isto que a rota precisa checar.
    allowed: bool
    # Visibilidade: aparece no menu? `allowed and not escondido por preferência`.
    visible: bool
    # Se a pessoa pode ligar/desligar isto na tela de preferências. Falso quando
    # está travado ou quando nem permissão ela tem — oferecer o botão nesse caso
    # seria prometer algo que o clique não cumpre.
    can_prefer: bool
    reason: Reason
    detail: str
    sources: list[str] = field(default_factory=list)


def _ceiling(
    surface_key: str,
    *,
    is_eg_admin: bool,
    enabled_modules: set[str],
    inaccessible_features: set[str],
) -> tuple[bool, Reason, str]:
    """Nível 1. Devolve (permitido, motivo, texto)."""
    if is_eg_admin:
        # A EG não assina módulo de si mesma nem espera a própria feature
        # amadurecer. O teto dela é aberto; o corte útil vem dos níveis 2-4.
        return True, "platform_admin", "Disponível para a equipe EG."

    module = surfaces.module_of(surface_key)
    if module and module not in enabled_modules:
        label = surfaces.entry(surface_key).get("label", surface_key)
        return False, "not_contracted", f"O módulo desta tela ({label}) não está contratado pela organização."

    feature_key = surfaces.feature_key_of(surface_key)
    if feature_key and feature_key in inaccessible_features:
        return False, "maturity", "Ainda não liberado para esta organização."

    return True, "default", "Disponível."


def resolve_surface(
    surface_key: str,
    *,
    is_eg_admin: bool,
    enabled_modules: set[str],
    inaccessible_features: set[str],
    team_grant: SurfaceGrant | None,
    user_grant: SurfaceGrant | None,
    hidden_by_preference: bool,
) -> SurfaceAccess:
    entry = surfaces.entry(surface_key)
    locked = bool(entry.get("locked"))
    sources: list[str] = []

    allowed, reason, detail = _ceiling(
        surface_key,
        is_eg_admin=is_eg_admin,
        enabled_modules=enabled_modules,
        inaccessible_features=inaccessible_features,
    )
    if not allowed:
        # Teto fechado encerra o assunto: nem equipe nem usuário reabrem.
        return SurfaceAccess(
            surface_key=surface_key,
            label=entry.get("label", surface_key),
            group=entry.get("group", "Outros"),
            parent=entry.get("parent"),
            locked=locked,
            allowed=False,
            visible=False,
            can_prefer=False,
            reason=reason,
            detail=detail,
            sources=["Organização"],
        )

    if reason == "platform_admin":
        sources.append("Equipe EG")

    # Nível 2 — equipe. (A fusão entre várias equipes já veio resolvida: quem
    # monta `team_grant` aplica "o mais restritivo vence".)
    if team_grant is not None:
        if team_grant.effect == "deny":
            allowed, reason = False, "team_denied"
            detail = f"Escondido para a equipe {team_grant.subject_label}."
        else:
            reason = "team_allowed"
            detail = f"Liberado para a equipe {team_grant.subject_label}."
        if team_grant.note:
            detail = f"{detail} {team_grant.note}"
        sources.append(f"Equipe {team_grant.subject_label}")

    # Nível 3 — usuário. Vence a equipe nos dois sentidos (ver docstring).
    if user_grant is not None:
        if user_grant.effect == "deny":
            allowed, reason = False, "user_denied"
            detail = "Bloqueado para você por um administrador."
        else:
            allowed, reason = True, "user_allowed"
            detail = "Liberado para você por um administrador."
        if user_grant.note:
            detail = f"{detail} {user_grant.note}"
        sources.append("Você (definido por um administrador)")

    if locked:
        # Trava vence tudo acima: é a garantia de que ninguém se tranca fora da
        # própria home. Vale inclusive contra um `deny` administrativo, porque
        # um admin negando o Cockpit para si mesmo não tem saída pela interface.
        allowed, reason = True, "locked"
        detail = "Sempre disponível — esta tela não pode ser ocultada."
        return SurfaceAccess(
            surface_key=surface_key,
            label=entry.get("label", surface_key),
            group=entry.get("group", "Outros"),
            parent=entry.get("parent"),
            locked=True,
            allowed=True,
            visible=True,
            can_prefer=False,
            reason=reason,
            detail=detail,
            sources=sources or ["Sempre disponível"],
        )

    # Nível 4 — preferência. Só subtrai, e só sobre o que já estava permitido.
    visible = allowed
    if allowed and hidden_by_preference:
        visible = False
        reason = "preference"
        detail = "Você escolheu ocultar esta tela. Continua acessível pela URL."
        sources.append("Sua preferência")

    return SurfaceAccess(
        surface_key=surface_key,
        label=entry.get("label", surface_key),
        group=entry.get("group", "Outros"),
        parent=entry.get("parent"),
        locked=False,
        allowed=allowed,
        visible=visible,
        can_prefer=allowed,
        reason=reason,
        detail=detail,
        sources=sources or ["Padrão"],
    )


def merge_team_grants(grants: list[tuple[str, str, str | None]]) -> SurfaceGrant | None:
    """Funde as exceções das várias equipes de uma pessoa numa só.

    `grants` = [(effect, team_name, note)]. **O mais restritivo vence**: basta
    uma equipe negar para o resultado ser negar, independentemente da ordem em
    que vieram do banco. Sem isso, entrar numa segunda equipe viraria a maneira
    mais fácil de recuperar um acesso que alguém tirou de propósito.
    """
    if not grants:
        return None
    for effect, team_name, note in grants:
        if effect == "deny":
            return SurfaceGrant(effect="deny", subject_label=team_name, note=note)
    effect, team_name, note = grants[0]
    return SurfaceGrant(effect="allow", subject_label=team_name, note=note)


def resolve_all(
    *,
    is_eg_admin: bool,
    enabled_modules: set[str],
    inaccessible_features: set[str],
    team_grants: dict[str, SurfaceGrant],
    user_grants: dict[str, SurfaceGrant],
    hidden_keys: set[str],
) -> list[SurfaceAccess]:
    return [
        resolve_surface(
            key,
            is_eg_admin=is_eg_admin,
            enabled_modules=enabled_modules,
            inaccessible_features=inaccessible_features,
            team_grant=team_grants.get(key),
            user_grant=user_grants.get(key),
            hidden_by_preference=key in hidden_keys,
        )
        for key in surfaces.keys_for_scope(is_eg_admin)
    ]
