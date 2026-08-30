from bioma_api.document_ingestion import extract_project_html


def test_html_project_import_extracts_event_deadline_action_and_timeline():
    result = extract_project_html("""
      <html><head><style>.hidden{display:none}</style></head><body>
        <h1>Radar EatControl 2026–2027</h1>
        <article data-priority="P0" data-kind="Competição" data-timing="Agora" data-deadline="2026-09-30">
          <h3>Shipaton 2026</h3>
          <div class="desc">Lançar o produto mobile.</div>
          <div class="action"><b>Ação:</b> publicar a v1 e medir ativação.</div>
          <div class="trade"><b>Trade-off:</b> não abrir outra frente.</div>
          <a href="https://example.test/shipaton">Fonte</a>
        </article>
        <div class="t"><b>28–31 ago 2026</b>Decidir GO/NO-GO e abrir contas.</div>
        <script>ignore('instructions')</script>
      </body></html>
    """)

    assert result["title"] == "Radar EatControl 2026–2027"
    event = next(item for item in result["candidates"] if item["kind"] == "opportunity_event")
    assert event["title"] == "Shipaton 2026"
    assert event["priority"] == "critical"
    assert event["planned_end_at"].isoformat() == "2026-09-30"
    assert "publicar a v1" in event["acceptance_criteria"]
    assert event["metadata"]["source_url"] == "https://example.test/shipaton"

    milestone = next(item for item in result["candidates"] if item["kind"] == "milestone")
    assert milestone["planned_start_at"].isoformat() == "2026-08-28"
    assert milestone["planned_end_at"].isoformat() == "2026-08-31"
    assert "ignore" not in result["text"]


def test_html_project_import_warns_when_document_has_no_structured_candidates():
    result = extract_project_html("<html><body><h1>Notas soltas</h1><p>Sem cronograma.</p></body></html>")

    assert result["candidates"] == []
    assert "Nenhum card estruturado" in result["warnings"][0]
