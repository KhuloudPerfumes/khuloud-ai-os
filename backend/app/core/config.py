from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "KHULOUD AI OS"
    environment: str = "local"
    api_base_url: str = "http://backend:8000"
    frontend_base_url: str = "http://localhost:3000"

    database_url: str = "postgresql+psycopg://khuloud:khuloud@postgres:5432/khuloud_ai_os"
    redis_url: str = "redis://redis:6379/0"
    qdrant_url: str = "http://qdrant:6333"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    product_source_url: str = "https://khuloudperfumes.com"
    image_generation_provider: str = "auto"
    gemini_api_key: str | None = None

    founder_email: str = "founder@khuloud.local"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    telegram_bot_token: str | None = None
    telegram_chat_id: str | None = None

    shopify_webhook_secret: str = "change-me"
    local_auth_username: str = "founder"
    local_auth_password: str = "change-me"

    config_dir: Path = Path(__file__).resolve().parents[1] / "config"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
