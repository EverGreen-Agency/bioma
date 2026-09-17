"""Smoke dos anexos do copiloto, contra o Postgres real.

O ponto do desenho: **o que vira texto funciona em qualquer provedor**. Um PDF
extraído roda no Codex CLI, na cota da assinatura, sem modelo com visão. E o que
NÃO deu para ler tem que chegar ao modelo dizendo que não deu — senão ele
responde sobre o arquivo como se tivesse lido.

Valida:
- só EG;
- extração por tipo: texto, csv (com cabeçalho por valor), json, pdf;
- imagem não tenta extrair texto (`not_needed`); tipo binário vira `unsupported`
  com o motivo escrito;
- conteúdo longo é cortado e o corte é contado, não silencioso;
- anexo ilegível chega ao dossiê com `unavailable_reason`;
- anexo de outra pessoa não é carregado nem passando o id na mensagem;
- a trilha guarda o índice do anexo, não o conteúdo (senão vira segunda cópia).

A extração roda direto (sem HTTP) porque o upload exige storage configurado, que
a CI não tem. O que depende de storage está marcado como tal.
"""

from pathlib import Path
import atexit
import io
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from bioma_api import attachment_text
from bioma_api.db import connect
from bioma_api.main import app
from bioma_api.repositories import copilot_attachments as repo
from bioma_api.services import copilot as copilot_service
from bioma_api.services import copilot_attachments as service
from smoke_support import cleanup_smoke_data, create_smoke_workspace, grant_client_user, upsert_smoke_user

ADMIN_EMAIL = "eduardo@evergreengrowth.com.br"
CLIENT_EMAIL = "smoke-attach-client@bioma.example.com"
PASSWORD = "senha-dev-123"


def assert_status(response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(f"{label}: esperado {expected}, recebido {response.status_code}: {response.text}")


def fake_plan(capture):
    def _plan(request):
        capture.append(request)
        return {
            "output": {
                "answer": "li o anexo",
                "actions": [],
                "sources": [],
                "confidence": "alta",
                "skills_used": [],
            },
            "generation_mode": "live",
            "provider": "fake",
            "model": "gpt-4o-mini",
            "usage": {"input_tokens": 100, "output_tokens": 10},
        }

    return _plan


def blank_pdf() -> bytes:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def main() -> None:
    workspace = create_smoke_workspace("ATTACH")
    client_user_id = upsert_smoke_user(CLIENT_EMAIL, "Attach Client Smoke", PASSWORD)
    grant_client_user(workspace, client_user_id)
    atexit.register(lambda: cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL]))
    workspace_id = str(workspace.workspace_id)

    admin = TestClient(app)
    client_user = TestClient(app)
    assert_status(admin.post("/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD}), 200, "login admin")
    assert_status(client_user.post("/auth/login", json={"email": CLIENT_EMAIL, "password": PASSWORD}), 200, "login cliente")

    # 1) Só EG (403 vem antes de qualquer necessidade de storage).
    assert_status(
        client_user.post("/copilot/attachments", files={"file": ("x.txt", b"oi", "text/plain")}),
        403,
        "cliente nao anexa",
    )
    print("escopo EG-only: 403 para client_user OK")

    # 2) Extração por tipo.
    txt = attachment_text.extract("Reunião com a Univet na sexta.".encode(), "text/plain", "nota.txt")
    assert txt["status"] == "extracted" and "Univet" in txt["text"], txt
    assert txt["truncated_chars"] == 0, "arquivo inteiro deveria ter corte zero, nao nulo"

    csv_result = attachment_text.extract(
        b"nome,cidade,nota\nPadaria X,Uberlandia,4.5\nBar Y,Araguari,3.9", "text/csv", "prospects.csv"
    )
    assert csv_result["status"] == "extracted", csv_result
    assert "nome=Padaria X" in csv_result["text"], (
        f"csv precisa levar o cabecalho junto de cada valor: {csv_result['text'][:200]}"
    )
    assert "Linhas: 2" in csv_result["text"], csv_result["text"][:200]

    json_result = attachment_text.extract(b'{"cliente":"Univet","mrr":4200}', "application/json", "dados.json")
    assert json_result["status"] == "extracted" and "Univet" in json_result["text"], json_result
    print("extracao de texto, csv com cabecalho por valor e json OK")

    # 3) PDF sem camada de texto: diz que é escaneado, não devolve vazio.
    pdf_result = attachment_text.extract(blank_pdf(), "application/pdf", "escaneado.pdf")
    assert pdf_result["status"] == "unsupported", pdf_result
    assert "camada de texto" in (pdf_result["error"] or ""), pdf_result["error"]
    print("pdf sem texto: recusado com o motivo (escaneado, precisaria de OCR) OK")

    # 4) Imagem não tenta extrair; binário desconhecido é recusado com motivo.
    image = attachment_text.extract(b"\x89PNG\r\n\x1a\n", "image/png", "print.png")
    assert image["status"] == "not_needed" and image["text"] is None, image
    binary = attachment_text.extract(b"PK\x03\x04\x00\x00\x00", "application/zip", "pacote.zip")
    assert binary["status"] == "unsupported" and binary["error"], binary
    assert attachment_text.classify("audio/mpeg", "call.mp3") == "audio"
    print("imagem nao extrai texto; binario recusado com motivo; audio classificado OK")

    # 4b) Transcricao real de audio (Whisper), mockada no nivel do bridge —
    # mesmo padrao usado no smoke de traducao: nunca finge sucesso sem chave.
    original_transcribe = service.transcribe_audio_safe
    try:
        service.transcribe_audio_safe = lambda content, file_name, content_type: {
            "text": "Reuniao marcada com a Univet na sexta.", "provider": "openai", "model": "whisper-1",
        }
        ok = service.transcribe_attachment_audio(b"fake-audio-bytes", "audio/mpeg", "call.mp3")
        assert ok["status"] == "extracted" and "Univet" in ok["text"], ok
        assert ok["truncated_chars"] == 0, ok
        print("transcricao de audio: chamou o whisper e extraiu o texto OK")

        service.transcribe_audio_safe = lambda content, file_name, content_type: {"text": "   "}
        empty = service.transcribe_attachment_audio(b"fake-audio-bytes", "audio/mpeg", "silencio.mp3")
        assert empty["status"] == "unsupported" and empty["text"] is None, empty
        print("transcricao vazia (sem fala reconhecivel): unsupported com motivo OK")

        def _raise(content, file_name, content_type):
            raise RuntimeError("Transcricao de audio exige OPENAI_API_KEY.")

        service.transcribe_audio_safe = _raise
        failed = service.transcribe_attachment_audio(b"fake-audio-bytes", "audio/mpeg", "call.mp3")
        assert failed["status"] == "failed" and "OPENAI_API_KEY" in failed["error"], failed
        print("sem OPENAI_API_KEY: anexo continua salvavel, so fica marcado como nao transcrito OK")

        service.transcribe_audio_safe = lambda content, file_name, content_type: {
            "text": "fala " * 10_000,
        }
        long_audio = service.transcribe_attachment_audio(b"fake-audio-bytes", "audio/mpeg", "longo.mp3")
        assert long_audio["status"] == "extracted", long_audio
        assert len(long_audio["text"]) == attachment_text.MAX_CHARS, len(long_audio["text"])
        assert long_audio["truncated_chars"] > 0, "corte da transcricao tambem precisa ser contado"
        print("transcricao longa: cortada e o corte e contado, igual aos outros tipos OK")
    finally:
        service.transcribe_audio_safe = original_transcribe

    # 5) Corte é contado, não silencioso.
    long_text = ("linha de conteudo repetida. " * 2000).encode()
    truncated = attachment_text.extract(long_text, "text/plain", "grande.txt")
    assert truncated["status"] == "extracted", truncated
    assert len(truncated["text"]) == attachment_text.MAX_CHARS, len(truncated["text"])
    assert truncated["truncated_chars"] > 0, "corte silencioso esconde que o modelo nao viu o arquivo todo"
    print(f"corte contado: {truncated['truncated_chars']} caractere(s) fora do contexto OK")

    attachment_ids: list[str] = []
    thread_ids: list[str] = []
    original_plan = copilot_service.copilot_plan_safe
    try:
        # 6) Anexo legível e anexo ilegível chegam ao dossiê — com a diferença explícita.
        with connect() as conn:
            admin_row = conn.execute(
                "select id from users where lower(email) = lower(%s)", (ADMIN_EMAIL,)
            ).fetchone()
            readable = repo.create(conn, {
                "thread_id": None, "user_id": admin_row["id"], "file_name": "briefing.txt",
                "content_type": "text/plain", "size_bytes": 42, "storage_key": "smoke/readable",
                "kind": "document", "extraction_status": "extracted",
                "extracted_text": "O cliente quer foco em captacao no Q3.", "truncated_chars": 0,
            })
            unreadable = repo.create(conn, {
                "thread_id": None, "user_id": admin_row["id"], "file_name": "call.mp3",
                "content_type": "audio/mpeg", "size_bytes": 90, "storage_key": "smoke/audio",
                "kind": "audio", "extraction_status": "pending",
            })
            # De outro usuário: não pode ser carregado nem passando o id.
            other = repo.create(conn, {
                "thread_id": None, "user_id": client_user_id, "file_name": "alheio.txt",
                "content_type": "text/plain", "size_bytes": 10, "storage_key": "smoke/other",
                "kind": "document", "extraction_status": "extracted", "extracted_text": "SEGREDO",
            })
            attachment_ids += [str(readable["id"]), str(unreadable["id"]), str(other["id"])]

            for_prompt, for_trace = service.load_for_prompt(
                conn, [readable["id"], unreadable["id"], other["id"]], admin_row["id"]
            )

        assert len(for_prompt) == 2, f"anexo de outro usuario vazou: {[i['file_name'] for i in for_prompt]}"
        assert not any("SEGREDO" in str(item) for item in for_prompt), for_prompt
        legivel = next(item for item in for_prompt if item["file_name"] == "briefing.txt")
        assert "captacao no Q3" in legivel["content"], legivel
        audio = next(item for item in for_prompt if item["file_name"] == "call.mp3")
        assert audio["content"] is None and "transcrição" in audio["unavailable_reason"], audio
        print("dossie leva o conteudo legivel e o MOTIVO do ilegivel; anexo alheio bloqueado OK")

        # 7) A trilha guarda o índice, não o conteúdo.
        assert not any("captacao no Q3" in str(item) for item in for_trace), (
            f"a trilha nao pode duplicar o conteudo do anexo: {for_trace}"
        )
        assert {item["file_name"] for item in for_trace} == {"briefing.txt", "call.mp3"}, for_trace
        print("trilha guarda indice (nome, tipo, status), nao o conteudo OK")

        # 8) Ponta a ponta: o anexo chega ao modelo e fica registrado na execução.
        captured: list[dict] = []
        copilot_service.copilot_plan_safe = fake_plan(captured)
        response = admin.post(
            "/copilot",
            json={
                "message": "o que diz o briefing?",
                "surface": "workspace",
                "workspace_id": workspace_id,
                "attachment_ids": [str(readable["id"])],
            },
        )
        assert_status(response, 200, "mensagem com anexo")
        thread_ids.append(response.json()["thread_id"])
        sent_dossier = captured[0]["dossier"]
        assert "captacao no Q3" in str(sent_dossier.get("attachments")), sent_dossier.get("attachments")

        trace = admin.get(f"/copilot/runs/{response.json()['run_id']}").json()
        assert len(trace["attachments"]) == 1, trace["attachments"]
        assert trace["attachments"][0]["file_name"] == "briefing.txt", trace["attachments"]
        assert trace["dossier_summary"]["attachments"] == 1, trace["dossier_summary"]
        print("anexo chegou ao modelo e ficou registrado na execucao OK")

        # 9) Anexo solto é adotado pela thread no envio.
        with connect() as conn:
            adopted = repo.get(conn, readable["id"])
        assert str(adopted["thread_id"]) == response.json()["thread_id"], (
            "anexo enviado antes da thread existir precisa ser adotado por ela"
        )
        print("anexo solto adotado pela conversa OK")
    finally:
        copilot_service.copilot_plan_safe = original_plan
        with connect() as conn:
            for thread_id in thread_ids:
                conn.execute("delete from copilot_threads where id = %s", (thread_id,))
            for attachment_id in attachment_ids:
                conn.execute("delete from copilot_attachments where id = %s", (attachment_id,))
        cleanup_smoke_data([workspace.organization_id], [CLIENT_EMAIL])
    print("limpeza OK — smoke_copilot_attachments passou")


if __name__ == "__main__":
    main()
