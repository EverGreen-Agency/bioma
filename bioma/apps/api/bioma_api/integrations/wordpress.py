"""Cliente REST do WordPress — decisão 14.

Contrato verificado na documentação oficial em 2026-08-11:
`POST /wp-json/wp/v2/posts` e Application Passwords (WordPress 5.6+) por Basic
Auth sobre HTTPS.
https://developer.wordpress.org/rest-api/reference/posts/
https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/

Alvo real confirmado no mesmo dia: a EG roda WordPress headless em
`cms.evergreenmkt.com.br`, com `application-passwords` anunciado no
`/wp-json/` e Rank Math instalado. O site Next.js da EG já consome esse CMS.

Duas regras que atravessam o arquivo inteiro:

1. **Nenhum erro devolve código cru.** "401" não diz a ninguém o que corrigir;
   "a Application Password foi revogada ou está errada" diz.
2. **A senha nunca entra em mensagem de erro.** Mensagem vai para log, tela e
   histórico ao mesmo tempo — um segredo que vaza por ali vaza para os três.
"""

from typing import Any

import httpx

TIMEOUT_SEGUNDOS = 20
_SUFIXOS_CONHECIDOS = ("/wp-json/wp/v2", "/wp-json", "")


class WordPressError(RuntimeError):
    """Falha ao falar com o WordPress, já traduzida para o que fazer."""


class WordPressClient:
    def __init__(
        self,
        site_url: str,
        username: str,
        app_password: str,
        http_client: httpx.Client | None = None,
    ):
        self._base = _normalizar(site_url)
        self._username = username
        # Preservado como veio: o WordPress exibe a senha em grupos de quatro
        # ("abcd EFGH ijkl") e aceita as duas formas. Quem cola, cola com
        # espaço — tirar por conta própria seria adivinhar.
        self._password = app_password
        self._segredo = app_password
        self._owns_client = http_client is None
        self._client = http_client or httpx.Client(timeout=TIMEOUT_SEGUNDOS)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def verify(self) -> dict[str, Any]:
        """Confere a credencial contra o site — sem escrever nada.

        `context=edit` de propósito: o WordPress só devolve esse contexto para
        quem tem permissão de edição, então a chamada responde de uma vez
        "a senha vale?" e "esse usuário consegue publicar?". Um GET anônimo
        passaria com credencial errada e daria falso positivo.
        """
        return self._request("GET", "/users/me", params={"context": "edit"})

    def create_post(self, payload: dict[str, Any]) -> dict[str, Any]:
        resposta = self._request("POST", "/posts", json=payload)
        if not resposta.get("id"):
            # 200 com corpo estranho é o pior caso: a tela diria "publicado" e
            # não haveria post nenhum. Foi exatamente o que o botão de sync fazia.
            raise WordPressError(
                "O WordPress respondeu sem identificar o post criado. "
                "Confira no painel se o post existe antes de tentar de novo."
            )
        return {
            "id": resposta["id"],
            "link": resposta.get("link"),
            "status": resposta.get("status"),
        }

    # ------------------------------------------------------------------ interno

    def _request(self, method: str, path: str, **kwargs) -> dict[str, Any]:
        try:
            resposta = self._client.request(
                method,
                f"{self._base}{path}",
                auth=(self._username, self._password),
                headers={"Accept": "application/json"},
                **kwargs,
            )
        except httpx.TimeoutException:
            raise WordPressError(
                f"O site não respondeu em {TIMEOUT_SEGUNDOS} segundos. "
                "Pode estar fora do ar ou muito lento."
            ) from None
        except httpx.HTTPError as erro:
            raise WordPressError(
                f"O site não respondeu: {self._limpar(str(erro))}"
            ) from None

        if resposta.status_code >= 400:
            raise WordPressError(self._explicar(resposta))

        return self._json(resposta)

    def _json(self, resposta: httpx.Response) -> dict[str, Any]:
        try:
            corpo = resposta.json()
        except ValueError:
            # Plugin de manutenção devolvendo HTML é o caso comum, e um
            # JSONDecodeError na tela não ajuda ninguém.
            raise WordPressError(
                "O site não devolveu JSON. Normalmente é plugin de manutenção, "
                "cache ou firewall interceptando a rota do WordPress."
            ) from None
        return corpo if isinstance(corpo, dict) else {"data": corpo}

    def _explicar(self, resposta: httpx.Response) -> str:
        codigo = resposta.status_code
        if codigo == 401:
            return (
                "Credencial recusada pelo WordPress. A Application Password foi "
                "revogada ou está errada — gere outra em Usuários › Perfil › "
                "Senhas de aplicativo."
            )
        if codigo == 403:
            return (
                "O usuário existe, mas não tem permissão para editar posts neste "
                "site. Use uma conta com papel de Autor ou acima."
            )
        if codigo == 404:
            return (
                "A REST API do WordPress não foi encontrada neste endereço. "
                "Confira a URL do site e se algum plugin de segurança não está "
                "bloqueando /wp-json/."
            )

        # 4xx de validação: o WordPress explica bem os próprios erros, e trocar
        # isso por texto genérico nosso perderia a única informação útil.
        try:
            mensagem = resposta.json().get("message")
        except ValueError:
            mensagem = None
        if mensagem:
            return f"O WordPress recusou: {self._limpar(str(mensagem))}"
        return f"O WordPress respondeu {codigo} sem explicar o motivo."

    def _limpar(self, texto: str) -> str:
        return texto.replace(self._segredo, "***") if self._segredo else texto


def _normalizar(site_url: str) -> str:
    """Aceita a URL na forma que a pessoa tiver em mãos.

    Home do site, `/wp-json`, ou o endpoint completo que ela já usa em outro
    lugar — todas chegam no mesmo lugar. Exigir uma forma específica é
    transformar um detalhe em chamado de suporte.
    """
    limpo = (site_url or "").strip().rstrip("/")
    if not limpo:
        raise WordPressError("Informe o endereço do site WordPress.")
    if not limpo.startswith("https://"):
        raise WordPressError(
            "O endereço precisa usar HTTPS. Application Password viaja em Basic "
            "Auth: sem TLS a senha vai em texto claro, e o WordPress só habilita "
            "esse método sob HTTPS."
        )
    for sufixo in _SUFIXOS_CONHECIDOS:
        if sufixo and limpo.endswith(sufixo):
            limpo = limpo[: -len(sufixo)]
            break
    return f"{limpo}/wp-json/wp/v2"
