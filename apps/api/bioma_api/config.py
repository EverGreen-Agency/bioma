from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: Literal["local", "staging", "production"] = "local"
    api_name: str = "Bioma API"
    database_url: str = "postgresql://bioma:bioma@localhost:5433/bioma"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174,https://www.evergreenmkt.com.br,https://evergreenmkt.com.br,https://bioma.evergreenmkt.com.br"
    session_cookie_name: str = "bioma_session"
    session_ttl_hours: int = 12
    session_cookie_secure: bool | None = None
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_domain: str | None = None
    login_rate_limit_attempts: int = 5
    login_rate_limit_window_seconds: int = 300
    # Domínios de e-mail aceitos ao convidar alguém para o time da EG.
    # Vazio (default) = sem restrição, que é o comportamento anterior — a lista
    # é guarda-corpo, não autenticação: privilégio vem de papel, nunca de
    # e-mail (foi por isso que o `endsWith` hardcoded saiu do App.tsx).
    #
    # Em configuração e não em código porque a EG tem mais de um domínio vivo
    # (evergreenmkt.com.br, evergreengrowth.com.br) e isso muda sem deploy.
    eg_invite_allowed_domains: str = ""
    github_api_token: str | None = None
    github_api_base_url: str = "https://api.github.com"
    # Aceitam DOIS nomes cada. O nosso (`STORAGE_S3_*`) e o que os serviços de
    # bucket injetam por conta própria (`BUCKET`, `ACCESS_KEY_ID`, ...).
    #
    # Motivo: quando a conexão entre serviços já existe no provedor, exigir
    # que alguém duplique a variável só para renomeá-la é trabalho manual que
    # existe por teimosia do nosso lado. O alias remove a etapa.
    #
    # O nome explícito vem PRIMEIRO de propósito: se os dois estiverem
    # presentes, ganha o nosso, que é inequívoco. O genérico é fallback —
    # `BUCKET` sozinho no ambiente é ambíguo se um dia houver dois buckets, e
    # nesse dia o jeito de desempatar é setar o nome explícito.
    storage_s3_bucket: str | None = Field(
        default=None, validation_alias=AliasChoices("STORAGE_S3_BUCKET", "BUCKET")
    )
    storage_s3_region: str = Field(
        default="auto", validation_alias=AliasChoices("STORAGE_S3_REGION", "REGION")
    )
    storage_s3_endpoint_url: str | None = Field(
        default=None, validation_alias=AliasChoices("STORAGE_S3_ENDPOINT_URL", "ENDPOINT_URL", "ENDPOINT")
    )
    storage_s3_access_key_id: str | None = Field(
        default=None, validation_alias=AliasChoices("STORAGE_S3_ACCESS_KEY_ID", "ACCESS_KEY_ID")
    )
    storage_s3_secret_access_key: str | None = Field(
        default=None, validation_alias=AliasChoices("STORAGE_S3_SECRET_ACCESS_KEY", "SECRET_ACCESS_KEY")
    )
    storage_s3_force_path_style: bool = True
    storage_max_upload_mb: int = 20
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    # Chave Fernet para segredos de integração em repouso (Kommo etc.).
    secret_encryption_key: str | None = None
    # Base pública da própria API (redirect_uri do OAuth) e do app web
    # (destino final dos redirects) — distintas porque web e API vivem em
    # subdomínios diferentes.
    api_public_url: str = "http://127.0.0.1:8000"
    web_app_url: str = "http://localhost:5173"
    # Benchmark de concorrentes (social-media do Ahrefs API v3) — usado só como
    # contexto de mercado na geração de roteiros, nunca fabricado sem a chave.
    ahrefs_api_key: str | None = None
    # OAuth por conexão (TikTok/LinkedIn não têm modelo de credencial única
    # compartilhada como o Google — cada cliente autoriza individualmente).
    tiktok_client_key: str | None = None
    tiktok_client_secret: str | None = None
    tiktok_ads_app_id: str | None = None
    tiktok_ads_secret: str | None = None
    linkedin_client_id: str | None = None
    linkedin_client_secret: str | None = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def invite_allowed_domain_list(self) -> list[str]:
        return [
            domain.strip().lower().lstrip("@")
            for domain in self.eg_invite_allowed_domains.split(",")
            if domain.strip()
        ]

    @property
    def storage_configured(self) -> bool:
        return bool(
            self.storage_s3_bucket and self.storage_s3_access_key_id and self.storage_s3_secret_access_key
        )

    @property
    def google_oauth_configured(self) -> bool:
        return bool(self.google_oauth_client_id and self.google_oauth_client_secret)

    @property
    def cookie_secure(self) -> bool:
        if self.session_cookie_secure is not None:
            return self.session_cookie_secure
        return self.app_env != "local"

    @model_validator(mode="after")
    def validate_deployment_settings(self) -> "Settings":
        if self.session_ttl_hours <= 0:
            raise ValueError("SESSION_TTL_HOURS precisa ser maior que zero.")

        if self.session_cookie_samesite == "none" and not self.cookie_secure:
            raise ValueError("SESSION_COOKIE_SAMESITE=none exige SESSION_COOKIE_SECURE=true.")

        if self.app_env != "local":
            if "localhost" in self.database_url or "127.0.0.1" in self.database_url:
                raise ValueError("DATABASE_URL de staging/produção não pode apontar para localhost.")
            if not self.cors_origin_list:
                raise ValueError("CORS_ORIGINS precisa declarar ao menos uma origem em staging/produção.")
            if any("localhost" in origin or "127.0.0.1" in origin for origin in self.cors_origin_list):
                raise ValueError("CORS_ORIGINS de staging/produção não pode conter origem local.")
            if not self.cookie_secure:
                raise ValueError("Cookies de sessão precisam ser Secure em staging/produção.")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
