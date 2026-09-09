"""
Application configuration — all values from environment variables.
Never hardcode secrets. Use .env.example as the template.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    project_id: str = "OIL_Pipeline_2026_Demo"

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://kranti:kranti_secret@localhost:5432/sih26122"
    )
    database_url_sync: str = Field(
        default="postgresql+psycopg2://kranti:kranti_secret@localhost:5432/sih26122"
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MinIO
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_raw: str = "sih-ingestion-raw"
    minio_bucket_extracted: str = "sih-ingestion-extracted"
    minio_secure: bool = False

    # WhatsApp
    whatsapp_app_secret: str = ""
    whatsapp_verify_token: str = ""
    whatsapp_access_token: str = ""
    whatsapp_phone_number_id: str = ""

    # LLM — NVIDIA NIM (PRIMARY for extraction and re-ranking)
    # Uses the OpenAI-compatible endpoint at integrate.api.nvidia.com.
    # Model: nvidia/nemotron-3-super-120b-a12b (120B total / 12B active MoE, 1M ctx).
    # Get a free API key at https://build.nvidia.com — no local GPU required.
    nvidia_api_key: str = ""
    nvidia_nim_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"

    # Confidence tiers (apply across ontology fields & matching)
    confidence_high_threshold: float = 0.90
    confidence_medium_threshold: float = 0.70

    # Matching thresholds
    match_auto_accept_threshold: float = 0.85
    match_review_threshold: float = 0.55

    # Vector DB — Qdrant
    # Separate collections for two distinct purposes (ADR-012):
    #   qdrant_collection_activities: matching-engine index (plan activities, for cosine lookup)
    #   qdrant_collection_events:     institutional memory (finalized actuals, for semantic recall)
    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection_events: str = "progress_events"
    qdrant_collection_activities: str = "plan_activities"

    # Auth (demo: named token store)
    reviewer_token: str = "dev-insecure-token"  # kept for backward compat with tests

    # faster-whisper
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"

    # File upload limits
    max_file_size_bytes: int = 50 * 1024 * 1024  # 50 MB

    @field_validator(
        "match_auto_accept_threshold",
        "match_review_threshold",
        "confidence_high_threshold",
        "confidence_medium_threshold",
    )
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0 and 1")
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached singleton Settings instance."""
    return Settings()
