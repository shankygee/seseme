"""
Application settings and configuration
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App settings
    app_name: str = "Companion Researcher"
    app_version: str = "1.0.0"
    debug: bool = True

    # API Keys (load from environment)
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    serpapi_key: Optional[str] = None
    tavily_api_key: Optional[str] = None

    # Paths
    base_dir: Path = Path(__file__).parent.parent.parent
    data_dir: Path = base_dir / "data"
    personalities_dir: Path = data_dir / "personalities"
    sessions_dir: Path = data_dir / "sessions"
    vector_db_dir: Path = data_dir / "vector_db"

    # LLM Settings
    default_llm_model: str = "gpt-4o"
    research_llm_model: str = "gpt-4o"
    summarization_llm_model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 4096

    # Research Settings
    max_search_results: int = 10
    max_sources_per_query: int = 5
    research_timeout: int = 60

    # Vector DB Settings
    embedding_model: str = "text-embedding-3-small"
    chunk_size: int = 500
    chunk_overlap: int = 50

    # CSM Voice Settings
    enable_voice: bool = True
    sample_rate: int = 24000

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
