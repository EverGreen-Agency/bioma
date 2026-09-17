"""Fluxo de publicação em CMS — decisão 14.

Cobre tudo que dá para provar SEM rede: cadastro do alvo, isolamento entre
workspaces, e a prévia — que é onde moram as regras de rascunho-vs-direto.

**Não chama o WordPress de verdade.** O envio real exige um site e uma
Application Password; o cliente HTTP tem 25 testes puros com
`httpx.MockTransport`. Fingir aqui que a integração inteira funciona seria o
verde falso que este repo já pagou caro para aprender a evitar.

O último bloco substitui a rede por um espião (`WordPressFalso`) — e a
distinção importa: ele não finge que publicar funciona, ele registra QUAL
método o serviço escolheu. É a única forma de provar a decisão criar-vs-atualizar,
que é onde estava o bug de post duplicado.
"""

import os
from pathlib import Path
import sys
from urllib.parse import urlparse

from cryptography.fernet import Fernet


os.environ.setdefault("SECRET_ENCRYPTION_KEY", Fernet.generate_key().decode("utf-8"))

SMOKE_DATABASE_URL = os.environ.get("BIOMA_SMOKE_DATABASE_URL")
if not SMOKE_DATABASE_URL:
    raise RuntimeError("Defina BIOMA_SMOKE_DATABASE_URL para executar smoke_cms_publish.py fora do banco operacional.")
smoke_database_name = urlparse(SMOKE_DATABASE_URL).path.lstrip("/").lower()
if not smoke_database_name.endswith(("_test", "_smoke")):
    raise RuntimeError("BIOMA_SMOKE_DATABASE_URL deve apontar para um banco com sufixo _test ou _smoke.")
os.environ["DATABASE_URL"] = SMOKE_DATABASE_URL

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.main import app  # noqa: E402
from bioma_api.services import cms as cms_service  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace, upsert_smoke_user  # noqa: E402


ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"

CONTEUDO = (
    "O investimento minimo e R$ 1.500 por mes, segundo o "
    "[relatorio da EverGreen](https://evergreenmkt.com.br/benchmarks).\n\n"
    "## Como calcular o orcamento?\n\n"
    "- Defina o CPC alvo pelo ticket medio\n"
    "- Reserve 30% para testes\n"
)


class WordPressFalso:
    """Substitui SO a rede. O que se prova aqui e a decisao do Bioma entre
    CRIAR e ATUALIZAR — que e onde estava o bug: `create_post` era chamado
    sempre, gerando post duplicado no site do cliente a cada republicacao.

    Nao e um WordPress de mentira para fingir que a integracao funciona; e um
    espiao para registrar qual metodo o servico escolheu."""

    chamadas: list[tuple[str, object]] = []

    def __init__(self, site_url, username, app_password, http_client=None):
        pass

    def close(self):
        pass

    def create_post(self, payload):
        WordPressFalso.chamadas.append(("create", None))
        return {"id": 101, "link": "https://cms.exemplo.com/?p=101", "status": payload.get("status")}

    def update_post(self, post_id, payload):
        WordPressFalso.chamadas.append(("update", str(post_id)))
        return {"id": post_id, "link": "https://cms.exemplo.com/?p=101", "status": payload.get("status")}


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def credential_payload(label: str) -> dict:
    return {
        "platform": "wordpress",
        "label": label,
        "secrets": {"username": "eduardo", "password": "abcd EFGH ijkl mnop qrst uvwx"},
    }


def main() -> None:
    workspace = create_smoke_workspace("CMS")
    outro = create_smoke_workspace("CMS Outro")
    upsert_smoke_user(ADMIN_EMAIL, "Eduardo", PASSWORD)

    try:
        with TestClient(app) as admin:
            login(admin, ADMIN_EMAIL)
            base = f"/workspaces/{workspace.workspace_id}/studio"

            credencial = admin.post(f"/workspaces/{workspace.workspace_id}/vault", json=credential_payload("WP EG"))
            assert_status(credencial, 201, "criar credencial no cofre")
            credential_id = credencial.json()["id"]

            alheia = admin.post(f"/workspaces/{outro.workspace_id}/vault", json=credential_payload("WP alheio"))
            assert_status(alheia, 201, "criar credencial no outro workspace")
            print("credenciais criadas no cofre OK")

            # --- alvo -------------------------------------------------------
            assert_status(
                admin.post(base + "/cms-targets", json={
                    "label": "Blog EG", "site_url": "http://inseguro.example.com",
                    "credential_id": credential_id,
                }),
                422,
                "HTTP sem TLS e recusado",
            )

            assert_status(
                admin.post(base + "/cms-targets", json={
                    "label": "Alvo torto", "site_url": "https://exemplo.com",
                    "credential_id": alheia.json()["id"],
                }),
                422,
                "credencial de outro workspace e recusada",
            )
            print("alvo recusa HTTP e credencial cruzada OK")

            alvo = admin.post(base + "/cms-targets", json={
                "label": "Blog EG", "site_url": "https://cms.exemplo.com",
                "credential_id": credential_id,
            })
            assert_status(alvo, 201, "criar alvo")
            target_id = alvo.json()["id"]
            assert alvo.json()["publish_mode"] == "draft", "o padrao TEM que ser rascunho"
            print("alvo criado com modo rascunho por padrao OK")

            # --- peça -------------------------------------------------------
            artefato = admin.post(base, json={
                "title": "Quanto custa anunciar no Google Ads",
                "kind": "artigo",
                "content": CONTEUDO,
            })
            assert_status(artefato, 201, "criar artefato")
            artifact_id = artefato.json()["id"]

            # --- prévia: alvo em rascunho ------------------------------------
            previa = admin.post(
                f"{base}/artifacts/{artifact_id}/publish-preview",
                json={"target_id": target_id},
            )
            assert_status(previa, 200, "previa com alvo em rascunho")
            corpo = previa.json()
            assert corpo["resulting_status"] == "draft", corpo
            assert corpo["downgrade_reason"] is None, "pedir rascunho e receber rascunho nao e rebaixamento"
            assert "<h2>Como calcular o orcamento?</h2>" in corpo["payload"]["content"], corpo["payload"]
            assert corpo["payload"]["slug"] == "quanto-custa-anunciar-no-google-ads", corpo["payload"]
            assert "author" not in corpo["payload"], "payload nao pode inventar autor"
            print("previa monta o payload sem enviar nada OK")

            # --- prévia: alvo em direto, peça NÃO aprovada -------------------
            assert_status(
                admin.patch(f"{base}/cms-targets/{target_id}", json={"publish_mode": "direct"}),
                200,
                "mudar alvo para publicar direto",
            )
            previa = admin.post(
                f"{base}/artifacts/{artifact_id}/publish-preview",
                json={"target_id": target_id},
            )
            assert_status(previa, 200, "previa com alvo em direto")
            corpo = previa.json()
            assert corpo["resulting_status"] == "draft", "peca nao aprovada NAO pode ir ao ar"
            assert corpo["downgrade_reason"], "o rebaixamento tem que explicar o motivo"
            print("alvo em 'direto' com peca nao aprovada rebaixa e explica OK")

            # --- prévia: alvo em direto, peça aprovada -----------------------
            assert_status(
                admin.patch(f"/artifacts/{artifact_id}/status", json={"status": "approved"}),
                200,
                "aprovar peca",
            )
            corpo = admin.post(
                f"{base}/artifacts/{artifact_id}/publish-preview",
                json={"target_id": target_id},
            ).json()
            assert corpo["resulting_status"] == "publish", corpo
            assert corpo["downgrade_reason"] is None, corpo
            print("peca aprovada em alvo direto vai como publish OK")

            # --- isolamento --------------------------------------------------
            assert_status(
                admin.post(
                    f"/workspaces/{outro.workspace_id}/studio/artifacts/{artifact_id}/publish-preview",
                    json={"target_id": target_id},
                ),
                404,
                "alvo de outro workspace nao e alcancavel",
            )

            assert_status(
                admin.post(
                    f"{base}/artifacts/{artifact_id}/publish-preview",
                    json={"target_id": target_id, "version": 99},
                ),
                404,
                "versao inexistente",
            )
            print("isolamento entre workspaces e versao inexistente OK")

            # --- alvo desativado não publica ---------------------------------
            assert_status(
                admin.patch(f"{base}/cms-targets/{target_id}", json={"is_active": False}),
                200,
                "desativar alvo",
            )
            recusa = admin.post(
                f"{base}/artifacts/{artifact_id}/publish",
                json={"target_id": target_id},
            )
            assert_status(recusa, 422, "alvo desativado nao publica")
            print("alvo desativado recusa publicacao OK")

            # --- republicar NAO pode duplicar ---------------------------------
            assert_status(
                admin.patch(f"{base}/cms-targets/{target_id}", json={"is_active": True}),
                200,
                "reativar alvo",
            )
            original = cms_service.WordPressClient
            cms_service.WordPressClient = WordPressFalso
            try:
                WordPressFalso.chamadas = []
                primeira = admin.post(f"{base}/artifacts/{artifact_id}/publish", json={"target_id": target_id})
                assert_status(primeira, 201, "primeira publicacao")
                assert WordPressFalso.chamadas == [("create", None)], WordPressFalso.chamadas

                segunda = admin.post(f"{base}/artifacts/{artifact_id}/publish", json={"target_id": target_id})
                assert_status(segunda, 201, "republicacao")
                assert WordPressFalso.chamadas[1] == ("update", "101"), (
                    f"republicar tem que ATUALIZAR o post 101, nao criar outro: {WordPressFalso.chamadas}"
                )

                publicacoes = admin.get(f"{base}/artifacts/{artifact_id}/publications").json()
                assert len(publicacoes) == 1, f"um artigo e UM post por alvo: {publicacoes}"
                assert publicacoes[0]["external_id"] == "101", publicacoes
            finally:
                cms_service.WordPressClient = original
            print("republicar ATUALIZA o mesmo post, nao duplica OK")

        print("limpeza OK - smoke_cms_publish passou")
    finally:
        cleanup_smoke_data([workspace.organization_id, outro.organization_id], [])


if __name__ == "__main__":
    main()
