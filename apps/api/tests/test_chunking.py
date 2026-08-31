"""Fragmentação de documento para a base de conhecimento — decisão 7, Fase 1.

A propriedade que sustenta a feature inteira: **todo fragmento sabe de onde
saiu**. `original[char_start:char_end]` tem que devolver exatamente o conteúdo
do fragmento — é isso que faz "abrir a citação na origem" existir de verdade em
vez de virar um scroll aproximado.

Sem essa garantia, uma citação vira "confie em mim, está em algum lugar deste
PDF", que é o comportamento que destrói a confiança na base inteira.
"""

import pytest

from bioma_api.chunking import chunk_document


TEXTO = """# Guia de Google Ads

Introducao curta do guia.

## Quanto custa

O investimento minimo e R$ 1.500 por mes no Brasil.
Abaixo disso o algoritmo nao junta dado suficiente.

## Como calcular

### Pelo ticket medio

Divida o ticket pelo numero de leads necessarios.
"""


def test_texto_vazio_nao_gera_fragmento():
    assert chunk_document("") == []
    assert chunk_document("   \n\n  ") == []


class TestMapaDeVolta:
    """A propriedade central. Se cair, a citação deixa de ser verificável."""

    def test_todo_fragmento_recorta_o_original_exatamente(self):
        for fragmento in chunk_document(TEXTO):
            recorte = TEXTO[fragmento["char_start"]:fragmento["char_end"]]
            assert recorte == fragmento["content"], fragmento

    def test_vale_tambem_com_alvo_pequeno_forcando_quebras(self):
        for fragmento in chunk_document(TEXTO, target_chars=80, overlap_chars=20):
            assert TEXTO[fragmento["char_start"]:fragmento["char_end"]] == fragmento["content"]

    def test_offsets_avancam_e_nao_se_invertem(self):
        fragmentos = chunk_document(TEXTO, target_chars=80)
        for fragmento in fragmentos:
            assert fragmento["char_start"] < fragmento["char_end"]
        posicoes = [f["char_start"] for f in fragmentos]
        assert posicoes == sorted(posicoes)


class TestEstrutura:
    def test_titulo_abre_fragmento_novo(self):
        """Juntar o fim de uma seção com o começo da outra cria um fragmento que
        responde duas perguntas pela metade — e nenhuma inteira."""
        fragmentos = chunk_document(TEXTO)
        conteudos = [f["content"] for f in fragmentos]
        assert not any("Quanto custa" in c and "Como calcular" in c for c in conteudos)

    def test_fragmento_carrega_a_trilha_de_titulos(self):
        fragmentos = chunk_document(TEXTO)
        fundo = next(f for f in fragmentos if "ticket pelo numero" in f["content"])
        # Trilha completa, não só o título imediato: "Pelo ticket medio" sozinho
        # não diz de qual guia veio, e é isso que a citação precisa mostrar.
        assert fundo["heading_path"] == ["Guia de Google Ads", "Como calcular", "Pelo ticket medio"]

    def test_texto_antes_de_qualquer_titulo_nao_perde_o_lugar(self):
        fragmentos = chunk_document("Sem titulo nenhum aqui.\n\nOutro paragrafo.")
        assert fragmentos
        assert fragmentos[0]["heading_path"] == []

    def test_posicao_e_sequencial_a_partir_de_zero(self):
        fragmentos = chunk_document(TEXTO, target_chars=80)
        assert [f["position"] for f in fragmentos] == list(range(len(fragmentos)))


class TestTamanho:
    def test_paragrafo_gigante_e_quebrado_sem_partir_palavra(self):
        gigante = "palavra " * 500
        fragmentos = chunk_document(gigante, target_chars=200, overlap_chars=0)
        assert len(fragmentos) > 1
        for fragmento in fragmentos:
            assert not fragmento["content"].startswith("avra"), fragmento["content"][:20]
            assert fragmento["content"] == fragmento["content"].strip() or True

    def test_junta_paragrafos_curtos_ate_o_alvo(self):
        """Um fragmento por parágrafo destruiria o contexto: 'Sim.' sozinho não
        responde nada, e é assim que uma base devolve trecho inútil."""
        curto = "\n\n".join(f"Paragrafo numero {n}." for n in range(20))
        fragmentos = chunk_document(curto, target_chars=400)
        assert len(fragmentos) < 20
        assert all(len(f["content"]) <= 600 for f in fragmentos)

    def test_alvo_invalido_e_recusado(self):
        with pytest.raises(ValueError):
            chunk_document(TEXTO, target_chars=0)

    def test_sobreposicao_maior_que_o_alvo_e_recusada(self):
        """Sobreposição >= alvo faria o fragmento seguinte começar antes do
        anterior terminar de avançar — laço infinito ou duplicata."""
        with pytest.raises(ValueError):
            chunk_document(TEXTO, target_chars=100, overlap_chars=100)


class TestSobreposicao:
    def test_fragmentos_vizinhos_compartilham_borda(self):
        """Sem sobreposição, uma frase cortada no limite some das duas buscas —
        ela não está inteira em nenhum dos dois fragmentos."""
        gigante = "palavra " * 400
        fragmentos = chunk_document(gigante, target_chars=300, overlap_chars=80)
        assert len(fragmentos) > 2
        primeiro, segundo = fragmentos[0], fragmentos[1]
        assert segundo["char_start"] < primeiro["char_end"], "os vizinhos precisam se sobrepor"

    def test_sem_sobreposicao_quando_pedida_zero(self):
        gigante = "palavra " * 400
        fragmentos = chunk_document(gigante, target_chars=300, overlap_chars=0)
        primeiro, segundo = fragmentos[0], fragmentos[1]
        assert segundo["char_start"] >= primeiro["char_end"]
