"""
Jarvis Backend Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Settings
    app_name: str = "Jarvis AI Assistant"
    debug: bool = False
    api_version: str = "v1"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    # Model Settings
    device: str = "cuda"  # or "cpu" for testing
    whisper_model: str = "large-v3"  # tiny, base, small, medium, large, large-v3
    use_faster_whisper: bool = True  # Use faster-whisper for speed

    # CSM Settings
    csm_model_path: Optional[str] = None  # Optional local path
    csm_max_audio_length_ms: int = 30000

    # Claude API
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Database
    database_url: str = "postgresql+asyncpg://jarvis:jarvis@localhost:5432/jarvis"

    # Audio Settings
    sample_rate: int = 24000  # CSM uses 24kHz

    # Security
    api_key_header: str = "X-API-Key"
    jwt_secret: str = "change-this-in-production"
    jwt_algorithm: str = "HS256"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
