"""Smoke do WhatsApp multi-provider: fábrica de providers + cifra do token em
repouso (mesmo padrão do Kommo — nunca texto puro no banco).

Roda in-process com TestClient em workspace isolado (self-clean).
"""

import os
import sys
from pathlib import Path

api_path = Path(__file__).resolve().parent.parent
worker_path = api_path.parent / "worker"
if str(api_path) not in sys.path:
    sys.path.insert(0, str(api_path))
if str(worker_path) not in sys.path:
    sys.path.insert(0, str(worker_path))

from cryptography.fernet import Fernet  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from bioma_api.config import get_settings  # noqa: E402
from bioma_api.db import connect  # noqa: E402
from bioma_api.main import app  # noqa: E402
from bioma_worker.providers.whatsapp import get_whatsapp_provider  # noqa: E402
from smoke_support import cleanup_smoke_data, create_smoke_workspace  # noqa: E402

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def login(client: TestClient, email: str) -> None:
    assert_status(client.post("/auth/login", json={"email": email, "password": PASSWORD}), 200, f"login {email}")


def main() -> None:
    print("Testing WhatsApp Multi-provider Architecture (Evolution, Meta Cloud, Z-API)...")

    # 1. Fábrica de providers (sem DB/HTTP).
    evo_provider = get_whatsapp_provider("evolution", {"instance_name": "instance_eg_01"})
    res_evo = evo_provider.send_text_message("5511999998888", "Olá! Teste Evolution API.")
    assert res_evo["status"] == "simulated"
    assert res_evo["provider"] == "evolution"

    meta_provider = get_whatsapp_provider("meta_cloud", {"instance_name": "phone_id_123"})
    res_meta = meta_provider.send_template_message("5511999998888", "hello_world", ["EverGreen"])
    assert res_meta["status"] == "simulated"
    assert res_meta["provider"] == "meta_cloud"

    zapi_provider = get_whatsapp_provider("zapi", {})
    res_zapi = zapi_provider.send_text_message("5511999998888", "Olá! Teste Z-API.")
    assert res_zapi["status"] == "simulated"
    assert res_zapi["provider"] == "custom"
    print("[OK] fábrica dos 3 providers (Evolution/Meta Cloud/Z-API)")

    workspace = create_smoke_workspace("WhatsAppWrite")
    admin = TestClient(app)

    original_key = os.environ.pop("SECRET_ENCRYPTION_KEY", None)
    try:
        login(admin, ADMIN_EMAIL)

        # 2. Sem SECRET_ENCRYPTION_KEY: gravar token deve falhar com 503, não guardar texto puro.
        get_settings.cache_clear()
        no_key = admin.post(
            f"/workspaces/{workspace.workspace_id}/whatsapp/providers",
            json={"provider_type": "evolution", "api_token": "token-nao-deveria-persistir", "instance_name": "inst-1"},
        )
        assert_status(no_key, 503, "sem SECRET_ENCRYPTION_KEY configurada")

        # 3. Com a chave configurada: o token é cifrado em repouso.
        os.environ["SECRET_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
        get_settings.cache_clear()

        created = admin.post(
            f"/workspaces/{workspace.workspace_id}/whatsapp/providers",
            json={
                "provider_type": "evolution",
                "api_token": "segredo-real-do-whatsapp",
                "instance_name": "instance_eg_01",
                "phone_number": "5511999998888",
                "status": "active",
                "metadata": {"engine": "baileys"},
            },
        )
        assert_status(created, 200, "criar provider com token")
        assert "api_token" not in created.json(), "api_token nunca deve voltar na resposta HTTP"

        with connect() as conn:
            raw = conn.execute(
                "select api_token from workspace_whatsapp_providers where workspace_id = %s and provider_type = 'evolution'",
                (workspace.workspace_id,),
            ).fetchone()
        assert raw["api_token"] != "segredo-real-do-whatsapp", "token gravado em texto puro no banco"
        assert raw["api_token"].startswith("enc:v1:"), f"token não está no formato cifrado esperado: {raw['api_token'][:20]}..."
        print("[OK] token cifrado em repouso (enc:v1:...), nunca em texto puro")

        # 4. Enviar mensagem decifra corretamente antes de repassar ao provider (sem exceção).
        sent = admin.post(
            f"/workspaces/{workspace.workspace_id}/whatsapp/send",
            json={"provider_type": "evolution", "to_number": "5511999998888", "message_text": "Smoke test"},
        )
        assert_status(sent, 201, "enviar mensagem com token cifrado")
        assert sent.json()["status"] in ("sent", "simulated"), sent.json()
        print("[OK] envio decifra o token e chega ao provider sem erro")

        logs = admin.get(f"/workspaces/{workspace.workspace_id}/whatsapp/logs")
        assert_status(logs, 200, "listar logs")
        assert len(logs.json()) == 1

        print("\nWHATSAPP MULTI-PROVIDER SMOKE TEST OK!")
    finally:
        cleanup_smoke_data([workspace.organization_id], [])
        if original_key is not None:
            os.environ["SECRET_ENCRYPTION_KEY"] = original_key
        else:
            os.environ.pop("SECRET_ENCRYPTION_KEY", None)
        get_settings.cache_clear()


if __name__ == "__main__":
    main()
