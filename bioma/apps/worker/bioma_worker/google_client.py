import json
from typing import Any

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account

from bioma_worker.config import WorkerSettings


def _parse_service_account(raw: str) -> dict:
    """Lê o JSON da service account e, quando falha, diz POR QUE.

    "JSON inválido" sozinho manda a pessoa conferir um valor de 2 KB sem pista
    do que procurar. As duas causas reais são conhecidas e têm sintoma
    distinto, então vale nomeá-las:

    1. **Quebra de linha na `private_key`.** O arquivo do Google traz
       `"private_key": "-----BEGIN...
MIIE..."` com `
` ESCAPADO. Editores de
       variável de ambiente (Railway incluso) costumam converter isso em quebra
       de linha real — e quebra de linha crua dentro de string é JSON inválido.
       É de longe o caso mais comum.
    2. **Valor entre aspas.** Colar o conteúdo já com aspas em volta faz o JSON
       virar uma string, não um objeto.

    O caso 2 é corrigido aqui (é inequívoco). O caso 1 NÃO é corrigido
    automaticamente de propósito: reescrever a chave privada às cegas poderia
    produzir uma credencial silenciosamente errada, e credencial que falha alto
    é melhor que credencial que autentica torto.
    """
    value = raw.strip()

    # Aspas em volta do valor inteiro: inequívoco, dá para desfazer.
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        value = value[1:-1].strip()

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        pista = ""
        if chr(10) in value and "private_key" in value:
            pista = (
                " Causa provável: a `private_key` está com quebras de linha REAIS. "
                "No arquivo do Google elas vêm como \n escapado — cole o conteúdo "
                "exatamente como está no .json baixado, sem passar por editor que "
                "reformata."
            )
        raise ValueError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON contém JSON inválido "
            f"(linha {exc.lineno}, coluna {exc.colno}: {exc.msg}).{pista}"
        ) from exc

    if not isinstance(parsed, dict):
        raise ValueError(
            "GOOGLE_SERVICE_ACCOUNT_JSON não é um objeto JSON — provavelmente o "
            "valor foi colado como texto entre aspas."
        )
    faltando = [campo for campo in ("client_email", "private_key", "token_uri") if not parsed.get(campo)]
    if faltando:
        raise ValueError(
            f"GOOGLE_SERVICE_ACCOUNT_JSON não parece ser uma service account: "
            f"faltam {', '.join(faltando)}. Baixe a chave em IAM › Contas de serviço › Chaves."
        )
    return parsed


class GoogleApiClient:
    def __init__(self, settings: WorkerSettings) -> None:
        self.settings = settings
        self._credentials: dict[tuple[str, ...], service_account.Credentials] = {}

    def request_json(
        self,
        method: str,
        url: str,
        scopes: tuple[str, ...],
        *,
        json_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        request_headers = {
            "Authorization": f"Bearer {self._access_token(scopes)}",
            "Content-Type": "application/json",
            **(headers or {}),
        }
        with httpx.Client(timeout=self.settings.google_request_timeout_seconds) as client:
            response = client.request(method, url, headers=request_headers, json=json_body)
        response.raise_for_status()
        return response.json()

    def _access_token(self, scopes: tuple[str, ...]) -> str:
        credentials = self._credentials.get(scopes)
        if credentials and credentials.valid and credentials.token:
            return credentials.token

        raw_credentials = self.settings.google_service_account_json
        if not raw_credentials:
            raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON não configurado no worker.")

        try:
            service_account_info = _parse_service_account(raw_credentials)
        except ValueError as exc:
            raise RuntimeError(str(exc)) from exc

        if credentials is None:
            credentials = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=list(scopes),
            )
            self._credentials[scopes] = credentials
        credentials.refresh(Request())
        if not credentials.token:
            raise RuntimeError("Google OAuth não retornou access token.")
        return credentials.token
