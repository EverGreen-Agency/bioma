"""Prontidão SEO/GEO de um texto — checklist executável, não previsão.

Decisão 14 (2026-08-11). O score responde "este texto está pronto para ser
publicado?" — e responde só com o que dá para verificar lendo o próprio texto.

**Não é previsão de ranking, e isso é uma decisão, não uma limitação temporária.**
Posição no Google depende de autoridade de domínio, backlinks, concorrência do
termo e histórico — nada disso está aqui. Um número chamado "SEO score: 85" que
a pessoa lê como "vou ficar em 85º lugar" é dado inventado com cara de
diagnóstico, e é justamente o que não entra neste produto.

Duas famílias, pontuadas separadamente de propósito:

- **SEO**: o que faz um buscador clássico entender e indexar a página.
- **GEO** (Generative Engine Optimization): o que faz um motor generativo
  CITAR o trecho. É outro jogo — resposta antes do contexto, subtítulo em
  forma de pergunta, número com fonte ao lado. Um texto pode ir muito bem num
  eixo e mal no outro, e uma média única esconderia exatamente isso.

Sem rede, sem banco, sem LLM: função pura, determinística, testável. O que
depende de julgamento (o texto está bom?) continua sendo trabalho de gente e
do copiloto — a checklist cuida do que é mecânico e, por ser mecânico, é o que
mais escapa na pressa.
"""

import re
from typing import Any, Literal

Family = Literal["seo", "geo"]

# Faixas de título: abaixo de 30 o título desperdiça espaço na SERP, acima de
# 60 o Google trunca. Não é lei, é o que cabe no pixel.
TITULO_MIN = 30
TITULO_MAX = 60

# "Resposta no início": o motor generativo lê o começo para decidir se o trecho
# responde a pergunta. 320 caracteres é cerca de um parágrafo.
JANELA_RESPOSTA = 320

MIN_PALAVRAS = 300

_MARKDOWN_IMG = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_MARKDOWN_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
_SUBTITULO = re.compile(r"^\s{0,3}#{2,6}\s+(.+)$", re.MULTILINE)
_ITEM_LISTA = re.compile(r"^\s{0,3}([-*+]|\d+\.)\s+\S", re.MULTILINE)
_NUMERO = re.compile(r"\d")
_ANO = re.compile(r"\b(19|20)\d{2}\b")


def evaluate_content(
    text: str,
    *,
    title: str = "",
    keyword: str | None = None,
) -> dict[str, Any]:
    """Avalia o texto e devolve score por família mais a lista de checks."""
    corpo = text or ""
    titulo = (title or "").strip()
    sem_marcacao = _strip_markdown(corpo)
    palavras = sem_marcacao.split()
    inicio = sem_marcacao[:JANELA_RESPOSTA]

    subtitulos = _SUBTITULO.findall(corpo)
    imagens = _MARKDOWN_IMG.findall(corpo)
    links = _MARKDOWN_LINK.findall(corpo)

    checks: list[dict[str, Any]] = [
        _check(
            "titulo_tamanho", "seo", "Título entre 30 e 60 caracteres",
            TITULO_MIN <= len(titulo) <= TITULO_MAX, 2,
            f"O título tem {len(titulo)} caracteres. Abaixo de {TITULO_MIN} desperdiça "
            f"espaço na busca; acima de {TITULO_MAX} o Google corta.",
        ),
        _check(
            "tamanho_texto", "seo", f"Pelo menos {MIN_PALAVRAS} palavras",
            len(palavras) >= MIN_PALAVRAS, 2,
            f"O texto tem {len(palavras)} palavras. Conteúdo curto raramente cobre "
            "a intenção de busca inteira.",
        ),
        _check(
            "subtitulos", "seo", "Tem subtítulos (H2/H3)",
            len(subtitulos) >= 2, 2,
            "Quebre o texto com ## subtítulos. Sem eles o buscador não sabe quais "
            "trechos respondem o quê.",
        ),
        _check(
            "links", "seo", "Tem pelo menos um link",
            len(links) >= 1, 1,
            "Adicione link para uma fonte ou para outra página do site.",
        ),
        _check(
            "imagem_alt", "seo", "Toda imagem tem texto alternativo",
            all(alt.strip() for alt, _ in imagens), 1,
            "Há imagem com alt vazio. O alt é o que o buscador (e o leitor de "
            "tela) enxerga no lugar da imagem.",
            # Texto sem imagem nenhuma não "passa" neste check: ele não se
            # aplica. Contar como aprovado dava 6 pontos a um texto VAZIO.
            applicable=bool(imagens),
        ),
        _check(
            "resposta_no_inicio", "geo", "Responde nos primeiros parágrafos",
            _NUMERO.search(inicio) is not None and len(inicio.strip()) > 80, 3,
            "Traga a resposta concreta (número, valor, prazo) para o primeiro "
            "parágrafo. Motor generativo cita o começo; contexto antes da resposta "
            "faz o trecho ser descartado.",
        ),
        _check(
            "subtitulo_pergunta", "geo", "Algum subtítulo em forma de pergunta",
            any("?" in sub for sub in subtitulos), 2,
            "Transforme ao menos um subtítulo em pergunta. É o formato que o "
            "motor casa com a pergunta do usuário.",
        ),
        _check(
            "dado_com_fonte", "geo", "Dado numérico com fonte ao lado",
            _tem_dado_com_fonte(corpo), 3,
            "Números aparecem sem link de fonte na mesma frase. Motor generativo "
            "cita o que consegue atribuir — número solto ele prefere não repetir.",
        ),
        _check(
            "lista", "geo", "Tem lista escaneável",
            _ITEM_LISTA.search(corpo) is not None, 1,
            "Inclua uma lista com marcadores. É o bloco mais fácil de extrair "
            "e citar inteiro.",
        ),
        _check(
            "recencia", "geo", "Marca temporal explícita",
            _ANO.search(corpo) is not None, 1,
            "Cite o ano ou a data de atualização. Sem isso o motor não consegue "
            "julgar se a informação ainda vale.",
        ),
    ]

    if keyword:
        alvo = keyword.strip().casefold()
        checks.extend([
            _check(
                "keyword_titulo", "seo", "Palavra-chave no título",
                alvo in titulo.casefold(), 2,
                f"O título não contém a palavra-chave '{keyword}'.",
            ),
            _check(
                "keyword_inicio", "seo", "Palavra-chave no primeiro parágrafo",
                alvo in inicio.casefold(), 1,
                f"A palavra-chave '{keyword}' não aparece no começo do texto.",
            ),
        ])

    return {
        "score": _score(checks),
        "seo_score": _score([c for c in checks if c["family"] == "seo"]),
        "geo_score": _score([c for c in checks if c["family"] == "geo"]),
        "words": len(palavras),
        "checks": checks,
    }


def _check(
    id_: str,
    family: Family,
    label: str,
    passed: bool,
    weight: int,
    hint: str,
    *,
    applicable: bool = True,
) -> dict[str, Any]:
    # `hint` só é útil quando reprova; guardamos sempre para a tela poder
    # mostrar o critério mesmo no check que passou.
    #
    # `applicable=False` significa "não há o que avaliar aqui" — sai do
    # denominador do score em vez de virar aprovação de graça.
    return {
        "id": id_,
        "family": family,
        "label": label,
        "passed": bool(passed) and applicable,
        "applicable": applicable,
        "weight": weight,
        "hint": hint,
    }


def _score(checks: list[dict[str, Any]]) -> int:
    checks = [check for check in checks if check["applicable"]]
    total = sum(check["weight"] for check in checks)
    if not total:
        return 0
    obtido = sum(check["weight"] for check in checks if check["passed"])
    return round(obtido * 100 / total)


def _tem_dado_com_fonte(corpo: str) -> bool:
    """Número e link na MESMA frase.

    Frase, não parágrafo: uma seção com link no rodapé e números soltos no meio
    não atribui nada, e passar isso premiaria exatamente o hábito que o check
    existe para corrigir.
    """
    for frase in re.split(r"(?<=[.!?])\s+|\n{2,}", corpo):
        if _NUMERO.search(frase) and _MARKDOWN_LINK.search(frase):
            return True
    return False


def _strip_markdown(corpo: str) -> str:
    limpo = _MARKDOWN_IMG.sub(" ", corpo)
    limpo = _MARKDOWN_LINK.sub(r"\1", limpo)
    limpo = re.sub(r"^\s{0,3}#{1,6}\s+", "", limpo, flags=re.MULTILINE)
    limpo = re.sub(r"[*_`>]", "", limpo)
    return re.sub(r"[ \t]+", " ", limpo).strip()
