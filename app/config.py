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
    secret_key: str = "change-me-in-production"
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
    jwt_secret: str = "change-this-jwt-secret"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60
    ted_api_base: str = "https://api.ted.europa.eu/v3"
    ocp_api_base: str = "https://data.open-contracting.org/api/3/action"

    # HuggingFace (local SLM)
    hf_api_token: Optional[str] = None
    hf_model_id: Optional[str] = None  # e.g. "mail2vimal11-arch/lexara-legal-saullm"
    use_local_llm: bool = False  # Set True to prefer HuggingFace over Claude
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
