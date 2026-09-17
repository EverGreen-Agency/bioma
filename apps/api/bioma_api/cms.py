"""Preparo de uma peça do Estúdio para publicação em CMS — decisão 14.

WordPress primeiro, com os outros CMS no horizonte. Por isso o módulo separa
**o que é da peça** (título, corpo, resumo, slug) do **que é do WordPress** (o
formato exato do payload em `build_post_payload`). Um segundo CMS troca a
segunda parte e reaproveita a primeira inteira.

Contrato verificado na documentação oficial em 2026-08-11:
`POST /wp-json/wp/v2/posts`, com `status` em `publish | future | draft |
pending | private`, autenticado por Application Password (WordPress 5.6+) via
Basic Auth sobre HTTPS.
https://developer.wordpress.org/rest-api/reference/posts/
https://developer.wordpress.org/rest-api/using-the-rest-api/authentication/

**Tudo aqui é função pura.** Montar o payload não envia nada — dá para mostrar
na tela exatamente o que iria para o site do cliente antes de qualquer chamada.
Num destino que é o site do CLIENTE, "ver antes" não é conforto: é o que separa
um erro corrigível de um post publicado em nome dele.
"""

import html as html_escape
import re
import unicodedata
from typing import Any, Literal

PublishMode = Literal["draft", "direct"]
WordPressStatus = Literal["draft", "publish"]

SLUG_MAX = 70
EXCERPT_MAX = 160

# Status do artefato no Bioma que autorizam publicação direta. `draft` e
# `archived` ficam de fora: a configuração diz COMO publicar, não SE a peça
# está pronta.
_LIBERADOS_PARA_PUBLICAR = frozenset({"approved", "published"})

_MD_LINK = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<![\*\w])\*([^*\n]+?)\*(?!\*)")
_MD_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*)$")
_MD_LISTITEM = re.compile(r"^\s{0,3}[-*+]\s+(.*)$")


def slugify(value: str, max_length: int = SLUG_MAX) -> str:
    """Título em slug — sem acento, minúsculo, separado por hífen.

    Corta em palavra inteira: um slug terminado no meio de uma palavra fica
    estranho no link e não ganha nada em troca.
    """
    sem_acento = unicodedata.normalize("NFKD", value or "")
    sem_acento = "".join(ch for ch in sem_acento if not unicodedata.combining(ch))
    limpo = re.sub(r"[^a-zA-Z0-9]+", "-", sem_acento).strip("-").lower()
    limpo = re.sub(r"-{2,}", "-", limpo)

    if len(limpo) <= max_length:
        return limpo
    cortado = limpo[:max_length]
    if "-" in cortado:
        cortado = cortado[: cortado.rindex("-")]
    return cortado.strip("-")


def resolve_publish_status(*, artifact_status: str, mode: PublishMode | None) -> WordPressStatus:
    """Decide entre rascunho e publicação no CMS.

    O padrão é RASCUNHO e a ausência de configuração conta como rascunho.
    Publicar por engano no site do cliente é o erro caro e difícil de desfazer;
    rascunho esquecido é o barato.

    E `direct` não vence a falta de aprovação: sem essa trava, marcar "direto"
    uma vez transformaria todo rascunho futuro em publicação automática — o
    oposto de uma configuração, que é uma escolha que continua sendo revista.
    """
    return explain_publish_status(artifact_status=artifact_status, mode=mode)[0]


def explain_publish_status(
    *, artifact_status: str, mode: PublishMode | None
) -> tuple[WordPressStatus, str | None]:
    """O status resolvido e, quando houve rebaixamento, o motivo.

    A tela precisa dizer POR QUE saiu rascunho num alvo configurado para
    publicar direto. Sem o motivo, a pessoa configura "direto", clica publicar,
    vê "rascunho" e conclui que a configuração está quebrada.

    Pedir rascunho e receber rascunho NÃO é rebaixamento — inventar um aviso aí
    treinaria a pessoa a ignorar avisos, que é como um aviso morre.
    """
    if mode != "direct":
        return "draft", None
    if artifact_status in _LIBERADOS_PARA_PUBLICAR:
        return "publish", None
    return "draft", (
        "O alvo está configurado para publicar direto, mas a peça ainda não foi "
        "aprovada no Bioma. Foi enviada como rascunho. Aprove a peça e publique "
        "de novo para ela ir ao ar."
    )


def capability_for_status(resulting_status: WordPressStatus) -> str:
    """Permissão exigida, atrelada ao RISCO e não ao botão.

    Publicar rascunho e publicar no ar são atos diferentes: o primeiro é
    reversível e invisível, o segundo aparece no site do cliente. Amarrar a
    permissão ao botão trataria os dois igual e obrigaria a escolher entre
    travar o rascunho ou liberar a publicação.

    Assim um operador rascunha à vontade e só quem aprova coloca no ar.
    """
    return "approve" if resulting_status == "publish" else "manage_work"


def markdown_to_html(text: str) -> str:
    """Conversão deliberadamente pequena: parágrafo, H2/H3, lista, link, ênfase.

    Não é um parser de Markdown completo, e não deve virar um. As peças do
    Estúdio saem do copiloto com essa marcação e nada mais; suportar tabela e
    footnote seria manter um parser inteiro para um caso que não existe.

    O texto é ESCAPADO antes de virar HTML. O destino é o site do cliente — um
    `<script>` no meio de uma peça não é risco nosso para correr.
    """
    linhas = (text or "").replace("\r\n", "\n").split("\n")
    blocos: list[str] = []
    paragrafo: list[str] = []
    lista: list[str] = []

    def fecha_paragrafo() -> None:
        if paragrafo:
            blocos.append(f"<p>{_inline(' '.join(paragrafo))}</p>")
            paragrafo.clear()

    def fecha_lista() -> None:
        if lista:
            itens = "\n".join(f"<li>{_inline(item)}</li>" for item in lista)
            blocos.append(f"<ul>\n{itens}\n</ul>")
            lista.clear()

    for linha in linhas:
        if not linha.strip():
            fecha_paragrafo()
            fecha_lista()
            continue

        cabecalho = _MD_HEADING.match(linha)
        if cabecalho:
            fecha_paragrafo()
            fecha_lista()
            # H1 vira H2: o H1 da página é o título do post, e um segundo H1 no
            # corpo confunde a hierarquia que o próprio checklist SEO cobra.
            nivel = max(2, min(6, len(cabecalho.group(1))))
            blocos.append(f"<h{nivel}>{_inline(cabecalho.group(2).strip())}</h{nivel}>")
            continue

        item = _MD_LISTITEM.match(linha)
        if item:
            fecha_paragrafo()
            lista.append(item.group(1).strip())
            continue

        fecha_lista()
        paragrafo.append(linha.strip())

    fecha_paragrafo()
    fecha_lista()
    return "\n".join(blocos)


def build_post_payload(
    artifact: dict[str, Any],
    *,
    mode: PublishMode | None,
    slug: str | None = None,
    categories: list[int] | None = None,
    tags: list[int] | None = None,
) -> dict[str, Any]:
    """Monta o corpo do `POST /wp/v2/posts` — sem enviar nada.

    Campos que a EG não tem como saber ficam FORA do payload, não em branco:
    `author` errado publica em nome de outra pessoa e `date` errado joga o post
    para o passado. Mesma lógica para `categories`/`tags`: lista vazia LIMPARIA
    a taxonomia no WordPress, enquanto omitir deixa o CMS aplicar o padrão dele.
    """
    conteudo = (artifact.get("content") or "").strip()
    if not conteudo:
        raise ValueError("A peça não tem conteúdo para publicar.")

    titulo = (artifact.get("title") or "").strip()
    payload: dict[str, Any] = {
        "title": titulo,
        "content": markdown_to_html(conteudo),
        "excerpt": _excerpt(conteudo),
        "slug": slug.strip() if slug and slug.strip() else slugify(titulo),
        "status": resolve_publish_status(
            artifact_status=str(artifact.get("status") or "draft"),
            mode=mode,
        ),
    }
    if categories:
        payload["categories"] = categories
    if tags:
        payload["tags"] = tags
    return payload


def _excerpt(conteudo: str) -> str:
    primeiro = ""
    for bloco in conteudo.split("\n\n"):
        limpo = bloco.strip()
        if not limpo or _MD_HEADING.match(limpo) or _MD_LISTITEM.match(limpo):
            continue
        primeiro = _MD_LINK.sub(r"\1", limpo).replace("**", "").replace("\n", " ")
        break

    if len(primeiro) <= EXCERPT_MAX:
        return primeiro
    # As reticencias contam para o limite: somar depois do corte estourava
    # EXCERPT_MAX em tres caracteres, e o limite existe porque o CMS trunca.
    cortado = primeiro[: EXCERPT_MAX - 3]
    if " " in cortado:
        cortado = cortado[: cortado.rindex(" ")]
    return cortado.rstrip(" ,;:") + "..."


def _inline(texto: str) -> str:
    # Escapar ANTES de aplicar a marcação: escapar depois transformaria as
    # próprias tags geradas aqui em texto visível.
    seguro = html_escape.escape(texto, quote=False)
    seguro = _MD_LINK.sub(lambda m: f'<a href="{html_escape.escape(m.group(2), quote=True)}">{m.group(1)}</a>', seguro)
    seguro = _MD_BOLD.sub(r"<strong>\1</strong>", seguro)
    seguro = _MD_ITALIC.sub(r"<em>\1</em>", seguro)
    return seguro
