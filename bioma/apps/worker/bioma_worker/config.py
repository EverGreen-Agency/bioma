from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    database_url: str = "postgresql://bioma:bioma@localhost:5433/bioma"
    google_service_account_json: str | None = None
    google_ads_developer_token: str | None = None
    google_ads_login_customer_id: str | None = None
    google_ads_api_version: str = "v21"
    google_request_timeout_seconds: float = 60
    meta_ads_access_token: str | None = None
    meta_ads_api_version: str = "v21.0"
    linkedin_ads_access_token: str | None = None
    linkedin_ads_api_version: str = "202504"
    instagram_access_token: str | None = None
    instagram_api_version: str = "v21.0"
    instagram_post_sync_limit: int = 50
    youtube_api_key: str | None = None
    google_places_api_key: str | None = None
    youtube_organic_sync_limit: int = 50
    secret_encryption_key: str | None = None
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_ads_app_id: str | None = None
    tiktok_ads_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None
    openai_api_key: str | None = None
    # Prober EXTERNO de disponibilidade. Fica em variável de ambiente (e não no
    # cofre) porque é credencial da agência, como o token do Google Ads — o
    # cofre guarda credencial de CLIENTE.
    betterstack_api_token: str | None = None
    # URL de heartbeat: o worker bate nela ao terminar. Sem isso, o cron parar
    # de disparar não gera erro nenhum — só silêncio.
    betterstack_heartbeat_url: str | None = None
    openai_model: str = "gpt-5.6-sol"
    openai_research_model: str = "gpt-5.6-terra"
    openai_transcription_model: str = "whisper-1"
    openai_request_timeout_seconds: float = 120
    codex_cli_path: str = "codex"
    claude_cli_path: str = "claude"
    antigravity_cli_path: str = "agy"
    ai_execution_timeout_seconds: int = 600
    openrouter_api_key: str | None = None
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_site_url: str = "https://bioma.evergreen.ag"
    openrouter_app_name: str = "Bioma"
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    gemini_api_key: str | None = None
    google_cloud_project: str | None = None
    google_cloud_location: str = "us-central1"
    ahrefs_api_key: str | None = None
    fathom_api_key: str | None = None
    fathom_request_timeout_seconds: float = 60
    # QUEUE-001: o lease precisa ser maior que o job mais longo esperado
    # (sync de 30 dias em 4 providers), senão o reaper reenfileira job vivo.
    # O heartbeat entre providers dá folga; 15 min é a margem para o resto.
    job_lease_seconds: int = 900
    job_max_attempts: int = 3

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
