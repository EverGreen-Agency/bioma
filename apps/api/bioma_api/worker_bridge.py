import sys
from pathlib import Path
from typing import Any

def _ensure_worker_in_path() -> bool:
    base = Path(__file__).resolve()
    for ancestor in [base] + list(base.parents):
        candidates = [
            ancestor / "bioma" / "apps" / "worker",
            ancestor / "apps" / "worker",
            ancestor / "worker",
        ]
        for candidate in candidates:
            if candidate.exists() and (candidate / "bioma_worker").exists():
                if str(candidate) not in sys.path:
                    sys.path.insert(0, str(candidate))
                return True
    return False

def get_whatsapp_provider_safe(provider_type: str, config_dict: dict[str, Any]) -> Any:
    _ensure_worker_in_path()
    try:
        from bioma_worker.providers.whatsapp import get_whatsapp_provider
        return get_whatsapp_provider(provider_type, config_dict)
    except ImportError as exc:
        raise RuntimeError("Provider WhatsApp indisponível no runtime.") from exc

def execute_squad_pipeline_safe(*args: Any, **kwargs: Any) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    try:
        from bioma_worker.squad_runner import execute_squad_pipeline
        from bioma_worker.config import get_settings
        pilar = kwargs.get("pilar")
        squad_name = kwargs.get("squad_key") or kwargs.get("squad_name")
        input_data = kwargs.get("input_context") or kwargs.get("input_data") or {}
        if not pilar or not squad_name:
            raise ValueError("pilar e squad_key/squad_name são obrigatórios.")
        return execute_squad_pipeline(pilar, squad_name, input_data, get_settings())
    except Exception as exc:
        raise RuntimeError("Falha ao executar o pipeline do squad.") from exc


def refine_market_sector_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    try:
        from bioma_worker.config import get_settings
        from bioma_worker.market_research import refine_market_sector

        return refine_market_sector(request, get_settings())
    except Exception as exc:
        raise RuntimeError("Falha ao refinar o setor para pesquisa.") from exc


def search_local_businesses_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.local_radar import search_local_businesses

    # Sem try/except genérico: o RuntimeError de chave ausente precisa chegar
    # intacto ao serviço para virar um 422 com a mensagem real.
    return search_local_businesses(request, get_settings())


def audit_local_prospect_safe(prospect: dict[str, Any], playbook: dict[str, Any] | None = None) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.local_radar import audit_local_prospect

    return audit_local_prospect(prospect, get_settings(), playbook=playbook)


def copilot_plan_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.copilot import plan

    return plan(request, get_settings())


def copilot_plan_routed_safe(request: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    """Plano do copiloto por uma conta do plano de roteamento.

    É o caminho que usa a COTA DA ASSINATURA (Codex CLI, Claude Code CLI,
    Antigravity) em vez de queimar chave de API avulsa.
    """
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.copilot import plan_via_candidate

    return plan_via_candidate(request, candidate, get_settings())


def probe_ai_provider_runtime_safe(account: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.provider_runtime import probe_provider_runtime

    return probe_provider_runtime(account, get_settings())


def pack_provider_credentials_safe(root: Path) -> str:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.provider_credentials import pack_credential_directory

    return pack_credential_directory(root)


def purge_provider_credentials_safe(account_id: Any) -> None:
    if not _ensure_worker_in_path():
        return
    from bioma_worker.provider_credentials import purge_provider_credential_cache

    purge_provider_credential_cache(account_id)


def ai_provider_settings_safe() -> Any:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings

    return get_settings()


def rank_copilot_candidates(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ordena as contas para o copiloto pelo mesmo critério dos workflows.

    `task_kind = reasoning`: o copiloto interpreta e decide, não gera conteúdo
    longo. Se houver política ativa para esse tipo, ela manda.
    """
    if not _ensure_worker_in_path():
        return []
    from bioma_worker.ai_routing import rank_candidates

    return rank_candidates({"task_kind": "reasoning", "capability": "reasoning"}, rows)


def copilot_plan_multistep_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.copilot import plan_multistep

    return plan_multistep(request, get_settings())


def platform_study_analyze_safe(request: dict[str, Any]) -> dict[str, Any]:
    """Pesquisa uma plataforma para decisão build vs. buy.

    Deixa a exceção subir: sem chave ou sem página legível, o serviço vira erro
    visível. Uma análise de "devo parar de construir o Bioma?" com resposta
    inventada seria o pior tipo de dado errado — o que parece decisão.
    """
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.platform_study import analyze

    return analyze(request, get_settings())


def platform_study_helpers() -> tuple[Any, Any]:
    """`derive_name` e `test_priority` — puro cálculo, sem rede nem modelo."""
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.platform_study import derive_name, test_priority

    return derive_name, test_priority


def translate_proposal_safe(payload: dict[str, Any]) -> dict[str, Any]:
    """Traduz uma proposta. Deixa a exceção subir — sem chave, o serviço vira
    erro visível, nunca uma tradução falsa com cara de traduzida."""
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.translation import translate_proposal

    return translate_proposal(payload, get_settings())


def transcribe_audio_safe(content: bytes, file_name: str, content_type: str) -> dict[str, Any]:
    """Transcreve um anexo de áudio via Whisper. Deixa a exceção subir — sem
    chave ou com a API fora do ar, o anexo fica marcado como não transcrito,
    nunca com um texto inventado no lugar do que foi dito."""
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.transcription import transcribe_audio

    return transcribe_audio(content, file_name, content_type, get_settings())


def copilot_action_catalog() -> dict[str, Any]:
    """Catalogo de acoes do copiloto. Fonte unica: o worker. A API valida
    reversibilidade contra ele antes de executar qualquer coisa."""
    if not _ensure_worker_in_path():
        return {}
    from bioma_worker.copilot import ACTION_CATALOG

    return ACTION_CATALOG


def analyze_sales_live_window_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.sales_live import analyze_live_window

    return analyze_live_window(request, get_settings())


def sales_live_suggestion_type(moment: str) -> str:
    if not _ensure_worker_in_path():
        return "question"
    from bioma_worker.sales_live import suggestion_type_for

    return suggestion_type_for(moment)


def list_fathom_meetings_safe(created_after: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.providers.fathom import list_meetings

    # Sem try/except generico: o RuntimeError de chave ausente precisa chegar
    # intacto ao servico para virar 422 com a mensagem real.
    return list_meetings(get_settings(), created_after=created_after, limit=limit)


def get_fathom_transcript_safe(recording_id: int | str) -> list[dict[str, Any]]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.providers.fathom import get_meeting_transcript

    return get_meeting_transcript(get_settings(), recording_id)


def generate_briefing_draft_safe(dossier: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.briefing import generate_briefing_draft
    from bioma_worker.config import get_settings

    return generate_briefing_draft(dossier, get_settings())


def generate_multichannel_insight_safe(totals: dict[str, Any]) -> dict[str, Any]:
    """Insight de midia paga. Sem chave, o worker devolve previa determinística
    rotulada — nunca recomendacao inventada."""
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma nao encontrado no runtime da API.")
    from bioma_worker.config import get_settings
    from bioma_worker.multichannel_insight import generate_multichannel_insight

    return generate_multichannel_insight(totals, get_settings())


def normalize_imported_prospects_safe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    from bioma_worker.local_radar import normalize_imported_prospects

    return normalize_imported_prospects(rows)


def generate_market_research_safe(request: dict[str, Any]) -> dict[str, Any]:
    if not _ensure_worker_in_path():
        raise RuntimeError("Worker do Bioma não encontrado no runtime da API.")
    try:
        from bioma_worker.config import get_settings
        from bioma_worker.market_research import generate_market_research

        return generate_market_research(request, get_settings())
    except Exception as exc:
        raise RuntimeError("Falha ao executar a pesquisa de mercado.") from exc
