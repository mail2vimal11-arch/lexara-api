"""Application configuration and settings."""

from pydantic_settings import BaseSettings
from typing import Optional


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
    
    # Database — default uses Docker Compose service name "db"
    database_url: str = "postgresql://lexara:lexara123@db:5432/lexaradb"

    # Redis — default uses Docker Compose service name "redis"
    redis_url: str = "redis://redis:6379/0"
    
    # API Keys
    claude_api_key: Optional[str] = None
    claude_model: str = "claude-haiku-4-5-20250514"  # override via CLAUDE_MODEL env var
    # receipts_api_key removed — CA-014: dead config, never referenced anywhere
    stripe_secret_key: Optional[str] = None   # CA-014: optional; billing disabled if unset
    stripe_publishable_key: Optional[str] = None
    stripe_webhook_secret: Optional[str] = None

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
    jwt_expire_minutes: int = 60
    ted_api_base: str = "https://api.ted.europa.eu/v3"
    ocp_api_base: str = "https://data.open-contracting.org/api/3/action"

    # Frontend URL (used in billing redirect defaults — CA-023/CA-030)
    frontend_url: str = "https://lexara.tech"

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
