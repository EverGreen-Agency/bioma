"""Fragmentação de documento para a base de conhecimento — decisão 7, Fase 1.

**A propriedade que sustenta a feature inteira:** todo fragmento sabe de onde
saiu. `original[char_start:char_end]` devolve exatamente `content`. É isso que
faz "abrir a citação na origem" existir de verdade, em vez de virar um scroll
aproximado e um "confie em mim, está em algum lugar deste PDF" — que é o
comportamento que destrói a confiança na base inteira.

Por isso o conteúdo **nunca é normalizado**: nada de colapsar espaço, remover
marcação ou reescrever. Qualquer edição no texto quebraria o mapa de volta, e o
mapa vale mais que a estética do fragmento.

Duas decisões de recorte:

- **Título abre fragmento novo.** Juntar o fim de uma seção com o começo da
  outra cria um fragmento que responde duas perguntas pela metade e nenhuma
  inteira.
- **Parágrafos curtos são agrupados até o alvo.** Um fragmento por parágrafo
  destruiria o contexto: "Sim." sozinho não responde nada, e é assim que uma
  base devolve trecho inútil com toda a confiança.

Sem embeddings, de propósito (Fase 1). O que este módulo produz alimenta busca
lexical do Postgres; quando a Fase 3 entrar, os mesmos fragmentos ganham vetor
sem precisar refragmentar.
"""

import re
from typing import Any

TARGET_CHARS = 1_200
OVERLAP_CHARS = 150

_CABECALHO = re.compile(r"^(#{1,6})[ \t]+(.+?)[ \t]*$", re.MULTILINE)


def chunk_document(
    text: str,
    *,
    target_chars: int = TARGET_CHARS,
    overlap_chars: int | None = None,
) -> list[dict[str, Any]]:
    """Fragmenta respeitando a estrutura, com offsets de volta ao original."""
    if target_chars <= 0:
        raise ValueError("target_chars precisa ser maior que zero.")

    if overlap_chars is None:
        # O PADRÃO se adapta ao alvo. Um default fixo de 150 fazia
        # `chunk_document(texto, target_chars=80)` estourar por causa de um
        # valor que quem chamou nem escolheu — e o padrão nunca deve ser o que
        # invalida uma chamada legítima. Valor EXPLÍCITO grande demais continua
        # sendo recusado logo abaixo, porque aí é escolha de quem chamou.
        overlap_chars = min(OVERLAP_CHARS, max(0, target_chars // 4))

    if overlap_chars < 0:
        raise ValueError("overlap_chars não pode ser negativo.")
    if overlap_chars >= target_chars:
        # Sobreposição >= alvo faria o fragmento seguinte começar antes de o
        # anterior terminar de avançar: laço infinito ou duplicata.
        raise ValueError("overlap_chars precisa ser menor que target_chars.")

    if not text or not text.strip():
        return []

    fragmentos: list[dict[str, Any]] = []
    for inicio, fim, trilha in _secoes(text):
        for corte_inicio, corte_fim in _cortes(text, inicio, fim, target_chars, overlap_chars):
            conteudo = text[corte_inicio:corte_fim]
            if not conteudo.strip():
                continue
            fragmentos.append(
                {
                    "position": len(fragmentos),
                    "content": conteudo,
                    "heading_path": list(trilha),
                    "char_start": corte_inicio,
                    "char_end": corte_fim,
                }
            )
    return fragmentos


def _secoes(text: str) -> list[tuple[int, int, list[str]]]:
    """Divide por título, carregando a TRILHA de títulos ancestrais.

    Trilha completa e não só o título imediato: "Pelo ticket médio" sozinho não
    diz de qual guia veio, e é justamente isso que a citação precisa mostrar.
    """
    cabecalhos = list(_CABECALHO.finditer(text))
    if not cabecalhos:
        return [(0, len(text), [])]

    secoes: list[tuple[int, int, list[str]]] = []

    # Texto antes do primeiro título não perde o lugar — vai sem trilha.
    if cabecalhos[0].start() > 0:
        secoes.append((0, cabecalhos[0].start(), []))

    pilha: list[tuple[int, str]] = []
    for indice, cabecalho in enumerate(cabecalhos):
        nivel = len(cabecalho.group(1))
        titulo = cabecalho.group(2).strip()
        while pilha and pilha[-1][0] >= nivel:
            pilha.pop()
        pilha.append((nivel, titulo))

        corpo_inicio = cabecalho.end()
        corpo_fim = cabecalhos[indice + 1].start() if indice + 1 < len(cabecalhos) else len(text)
        if text[corpo_inicio:corpo_fim].strip():
            secoes.append((corpo_inicio, corpo_fim, [item[1] for item in pilha]))
    return secoes


def _cortes(
    text: str, inicio: int, fim: int, target_chars: int, overlap_chars: int
) -> list[tuple[int, int]]:
    """Onde cortar dentro de uma seção, em offsets do texto ORIGINAL."""
    blocos = _paragrafos(text, inicio, fim)
    if not blocos:
        return []

    cortes: list[tuple[int, int]] = []
    atual_inicio: int | None = None
    atual_fim: int | None = None

    for bloco_inicio, bloco_fim in blocos:
        tamanho = bloco_fim - bloco_inicio

        # Parágrafo maior que o alvo sozinho: fecha o que estiver aberto e
        # quebra ele em janelas, sempre em fronteira de palavra.
        if tamanho > target_chars:
            if atual_inicio is not None:
                cortes.append((atual_inicio, atual_fim))
                atual_inicio = atual_fim = None
            cortes.extend(_janelas(text, bloco_inicio, bloco_fim, target_chars, overlap_chars))
            continue

        if atual_inicio is None:
            atual_inicio, atual_fim = bloco_inicio, bloco_fim
        elif bloco_fim - atual_inicio <= target_chars:
            atual_fim = bloco_fim
        else:
            cortes.append((atual_inicio, atual_fim))
            atual_inicio, atual_fim = bloco_inicio, bloco_fim

    if atual_inicio is not None:
        cortes.append((atual_inicio, atual_fim))
    return cortes


def _paragrafos(text: str, inicio: int, fim: int) -> list[tuple[int, int]]:
    """Fronteiras de parágrafo dentro do trecho, em offsets do original."""
    blocos: list[tuple[int, int]] = []
    cursor = inicio
    for separador in re.finditer(r"\n[ \t]*\n", text[inicio:fim]):
        bloco_fim = inicio + separador.start()
        if text[cursor:bloco_fim].strip():
            blocos.append(_apertar(text, cursor, bloco_fim))
        cursor = inicio + separador.end()
    if text[cursor:fim].strip():
        blocos.append(_apertar(text, cursor, fim))
    return blocos


def _janelas(
    text: str, inicio: int, fim: int, target_chars: int, overlap_chars: int
) -> list[tuple[int, int]]:
    """Quebra um parágrafo longo em janelas, cortando em fronteira de palavra.

    A sobreposição existe porque, sem ela, uma frase cortada no limite some das
    duas buscas — ela não está inteira em nenhum dos dois fragmentos.
    """
    janelas: list[tuple[int, int]] = []
    cursor = inicio
    while cursor < fim:
        limite = min(cursor + target_chars, fim)
        if limite < fim:
            espaco = text.rfind(" ", cursor, limite)
            # Só recua se sobrar corpo: um espaço logo no começo faria a janela
            # nascer vazia e o laço nunca avançar.
            if espaco > cursor:
                limite = espaco
        janelas.append(_apertar(text, cursor, limite))
        if limite >= fim:
            break
        proximo = max(cursor + 1, limite - overlap_chars)
        cursor = proximo
    return janelas


def _apertar(text: str, inicio: int, fim: int) -> tuple[int, int]:
    """Tira espaço em branco das bordas MOVENDO OS OFFSETS.

    Não usa `.strip()` no conteúdo: cortar a string sem mover o offset romperia
    a igualdade `original[start:end] == content`, que é a garantia inteira
    deste módulo.
    """
    while inicio < fim and text[inicio].isspace():
        inicio += 1
    while fim > inicio and text[fim - 1].isspace():
        fim -= 1
    return inicio, fim
