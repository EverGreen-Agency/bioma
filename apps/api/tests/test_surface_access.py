"""Resolução dos 4 níveis de acesso (`bioma_api.surface_access`).

Testa a regra, não o encanamento: a resolução é função pura, então cada caso
aqui fixa uma decisão de produto que alguém poderia desfazer sem perceber.

Os dois invariantes que não podem quebrar nunca:
- preferência pessoal NUNCA concede o que a permissão nega;
- o teto da organização não se fura por equipe nem por usuário.
"""

import pytest

from bioma_api import surfaces
from bioma_api.surface_access import SurfaceGrant, merge_team_grants, resolve_all, resolve_surface

EG_MODULES: set[str] = set()
CLIENT_MODULES = {"hub", "content", "files"}


def eg(surface_key: str, **kwargs):
    base = dict(
        is_eg_admin=True,
        enabled_modules=EG_MODULES,
        inaccessible_features=set(),
        team_grant=None,
        user_grant=None,
        hidden_by_preference=False,
    )
    base.update(kwargs)
    return resolve_surface(surface_key, **base)  # type: ignore[arg-type]


def client(surface_key: str, **kwargs):
    base = dict(
        is_eg_admin=False,
        enabled_modules=CLIENT_MODULES,
        inaccessible_features=set(),
        team_grant=None,
        user_grant=None,
        hidden_by_preference=False,
    )
    base.update(kwargs)
    return resolve_surface(surface_key, **base)  # type: ignore[arg-type]


class TestTetoDaOrganizacao:
    def test_cliente_sem_modulo_contratado_nao_entra(self):
        # `analytics` não está em CLIENT_MODULES.
        result = client("cliente.analytics")
        assert result.allowed is False
        assert result.reason == "not_contracted"

    def test_cliente_com_modulo_contratado_entra(self):
        result = client("cliente.conteudo-ia")
        assert result.allowed is True

    def test_feature_imatura_bloqueia_mesmo_com_modulo(self):
        # Módulo contratado, feature ainda não liberada: são eixos diferentes.
        result = client("cliente.conteudo-ia", inaccessible_features={"local_radar"})
        assert result.allowed is True  # esta superfície não depende daquela flag

        radar = resolve_surface(
            "operacao.radar-local",
            is_eg_admin=False,
            enabled_modules=CLIENT_MODULES,
            inaccessible_features={"local_radar"},
            team_grant=None,
            user_grant=None,
            hidden_by_preference=False,
        )
        assert radar.allowed is False
        assert radar.reason == "maturity"

    def test_eg_admin_ignora_teto(self):
        # A EG não contrata módulo de si mesma.
        assert eg("cliente.analytics").allowed is True
        assert eg("operacao.radar-local", inaccessible_features={"local_radar"}).allowed is True

    def test_allow_de_usuario_nao_fura_o_teto(self):
        """O caso que mais importa: exceção de usuário não vira escada."""
        result = client(
            "cliente.analytics",
            user_grant=SurfaceGrant(effect="allow", subject_label="Fulano"),
        )
        assert result.allowed is False
        assert result.reason == "not_contracted"

    def test_allow_de_equipe_nao_fura_o_teto(self):
        result = client(
            "cliente.analytics",
            team_grant=SurfaceGrant(effect="allow", subject_label="Growth"),
        )
        assert result.allowed is False


class TestEquipe:
    def test_deny_de_equipe_esconde(self):
        result = eg("eg-rh", team_grant=SurfaceGrant(effect="deny", subject_label="Growth"))
        assert result.allowed is False
        assert result.reason == "team_denied"
        assert "Growth" in result.detail

    def test_mais_restritivo_vence_entre_equipes(self):
        # Duas equipes, uma nega: nega. A ordem não pode importar.
        merged = merge_team_grants([("allow", "Growth", None), ("deny", "Social", None)])
        assert merged is not None and merged.effect == "deny"

        invertido = merge_team_grants([("deny", "Social", None), ("allow", "Growth", None)])
        assert invertido is not None and invertido.effect == "deny"

    def test_sem_equipe_nao_muda_nada(self):
        assert merge_team_grants([]) is None


class TestUsuarioVenceEquipe:
    def test_allow_de_usuario_devolve_o_que_a_equipe_tirou(self):
        result = eg(
            "eg-rh",
            team_grant=SurfaceGrant(effect="deny", subject_label="Growth"),
            user_grant=SurfaceGrant(effect="allow", subject_label="Fulano"),
        )
        assert result.allowed is True
        assert result.reason == "user_allowed"

    def test_deny_de_usuario_vence_allow_de_equipe(self):
        result = eg(
            "eg-rh",
            team_grant=SurfaceGrant(effect="allow", subject_label="Growth"),
            user_grant=SurfaceGrant(effect="deny", subject_label="Fulano"),
        )
        assert result.allowed is False
        assert result.reason == "user_denied"


class TestPreferenciaPessoal:
    def test_preferencia_esconde_mas_nao_tira_permissao(self):
        result = eg("eg-rh", hidden_by_preference=True)
        assert result.allowed is True   # a rota continua respondendo
        assert result.visible is False  # o menu não mostra
        assert result.reason == "preference"

    def test_preferencia_nao_concede_o_que_a_permissao_nega(self):
        """Invariante central da decisão 11."""
        result = client("cliente.analytics", hidden_by_preference=True)
        assert result.allowed is False
        assert result.visible is False
        # O motivo continua sendo a permissão, não a preferência — senão a tela
        # explicaria errado e a pessoa pediria para "reexibir" algo que nunca
        # foi escolha dela.
        assert result.reason == "not_contracted"

    def test_negado_nao_oferece_botao_de_preferencia(self):
        assert client("cliente.analytics").can_prefer is False
        assert eg("eg-rh").can_prefer is True


class TestTravadas:
    def test_cockpit_nao_pode_ser_escondido(self):
        result = eg("cockpit", hidden_by_preference=True)
        assert result.visible is True
        assert result.reason == "locked"

    def test_trava_vence_deny_administrativo(self):
        # Ninguém se tranca fora da própria home, nem por engano de admin.
        result = eg("cockpit", user_grant=SurfaceGrant(effect="deny", subject_label="Fulano"))
        assert result.allowed is True

    def test_hub_do_cliente_e_travado_para_o_cliente(self):
        assert client("cliente.hub", hidden_by_preference=True).visible is True


class TestExplicacaoNaTela:
    def test_toda_superficie_tem_motivo_e_texto(self):
        """"Por que não vejo o RH?" precisa ter resposta em 100% dos casos."""
        for result in resolve_all(
            is_eg_admin=True,
            enabled_modules=EG_MODULES,
            inaccessible_features=set(),
            team_grants={"eg-rh": SurfaceGrant(effect="deny", subject_label="Growth")},
            user_grants={},
            hidden_keys={"eg-kits"},
        ):
            assert result.detail, f"{result.surface_key} ficou sem explicação"
            assert result.sources, f"{result.surface_key} ficou sem origem"

    def test_origem_aponta_a_equipe_que_negou(self):
        result = eg("eg-rh", team_grant=SurfaceGrant(effect="deny", subject_label="Growth"))
        assert any("Growth" in source for source in result.sources)


class TestCatalogo:
    def test_escopo_separa_telas_de_eg_e_de_cliente(self):
        eg_keys = set(surfaces.keys_for_scope(is_eg=True))
        client_keys = set(surfaces.keys_for_scope(is_eg=False))
        assert "eg-rh" in eg_keys and "eg-rh" not in client_keys
        assert "cliente.hub" in client_keys and "cliente.hub" in eg_keys

    def test_modulos_do_catalogo_existem_na_politica_de_acesso(self):
        """Um `module` escrito errado viraria bloqueio silencioso e permanente."""
        from bioma_api.access import CLIENT_MODULES as VALID_MODULES

        for key, entry in surfaces.SURFACE_CATALOG.items():
            module = entry.get("module")
            if module is not None:
                assert module in VALID_MODULES, f"{key} aponta módulo inexistente: {module}"

    def test_feature_keys_do_catalogo_existem(self):
        from bioma_api.feature_flags import FEATURE_CATALOG

        for key, entry in surfaces.SURFACE_CATALOG.items():
            feature_key = entry.get("feature_key")
            if feature_key is not None:
                assert feature_key in FEATURE_CATALOG, f"{key} aponta feature inexistente: {feature_key}"

    def test_parent_aponta_superficie_existente(self):
        for key, entry in surfaces.SURFACE_CATALOG.items():
            parent = entry.get("parent")
            if parent is not None:
                assert surfaces.is_known(parent), f"{key} tem pai inexistente: {parent}"


@pytest.mark.parametrize("surface_key", sorted(surfaces.SURFACE_CATALOG))
def test_resolucao_nunca_estoura(surface_key: str):
    """Catálogo e resolução não podem sair de sincronia sem alguém notar."""
    result = resolve_surface(
        surface_key,
        is_eg_admin=True,
        enabled_modules=EG_MODULES,
        inaccessible_features=set(),
        team_grant=None,
        user_grant=None,
        hidden_by_preference=False,
    )
    assert result.surface_key == surface_key
    assert result.label
