"""Application configuration and settings."""

import logging
from pydantic_settings import BaseSettings
from typing import Optional

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings from environment variables."""
    
    # App
    app_name: str = "LexAra API"
    version: str = "1.0.0"
    debug: bool = False
    environment: str = "production"
    secret_key: str
    port: int = 8000
    log_level: str = "INFO"
    
    # Database
    database_url: str = "postgresql://localhost/lexrisk"
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # API Keys
    claude_api_key: str
    receipts_api_key: str
    stripe_secret_key: str
    stripe_publishable_key: str
    stripe_webhook_secret: str

    # Stripe Price IDs
    stripe_price_starter:  str = "price_1TI9WfPGiwBBvDi6P0GacboQ"
    stripe_price_growth:   str = "price_1TI9WgPGiwBBvDi67TCKlqT5"
    stripe_price_business: str = "price_1TI9WgPGiwBBvDi6CwOp0cAu"
    
    # CORS
    allowed_origins: str = "http://localhost:3000,https://lexrisk.com"
    
    # Email
    smtp_server: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    
    # Feature flags
    enable_async_processing: bool = True
    enable_caching: bool = True
    enable_webhooks: bool = True

    # Procurement AI
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours — legal professionals need extended sessions
    ted_api_base: str = "https://api.ted.europa.eu/v3"
    ocp_api_base: str = "https://data.open-contracting.org/api/3/action"

    # HuggingFace (local SLM)
    hf_api_token: Optional[str] = None
    hf_model_id: Optional[str] = None  # e.g. "mail2vimal11-arch/lexara-legal-saullm"
    use_local_llm: bool = False  # Set True to prefer HuggingFace over Claude

    # Groq (free fast inference)
    groq_api_key: Optional[str] = None
    groq_model: str = "llama-3.1-8b-instant"
    use_groq: bool = False  # Set True to prefer Groq over Claude
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"


settings = Settings()


def _warn_on_misconfigured_llm_flags() -> None:
    """Surface waterfall flags that are silently disabled despite credentials being present.

    The 3-tier waterfall (Groq → HuggingFace → Claude) only routes to a free tier
    when BOTH the feature flag AND the credentials are set. A missing flag is the
    most common deployment mistake — operators set the API key in .env and assume
    it's wired up, but every request silently falls through to paid Claude.
    """
    if settings.groq_api_key and not settings.use_groq:
        logger.warning(
            "GROQ_API_KEY is set but USE_GROQ=false — Groq tier will be skipped "
            "and requests will fall through to Claude (paid). "
            "Set USE_GROQ=true to enable the free tier."
        )
    if settings.hf_api_token and not settings.use_local_llm:
        logger.warning(
            "HF_API_TOKEN is set but USE_LOCAL_LLM=false — HuggingFace tier will "
            "be skipped and requests will fall through to Claude (paid). "
            "Set USE_LOCAL_LLM=true to enable the SaulLM tier."
        )
    if settings.use_local_llm and settings.hf_api_token and not settings.hf_model_id:
        logger.warning(
            "USE_LOCAL_LLM=true and HF_API_TOKEN is set but HF_MODEL_ID is empty — "
            "HuggingFace tier will be skipped. Set HF_MODEL_ID to the deployed model."
        )


_warn_on_misconfigured_llm_flags()
