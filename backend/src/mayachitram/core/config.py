from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MAYACHITRAM_", env_file=".env", extra="ignore")

    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    max_upload_bytes: int = Field(default=10 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_vision_model: str = Field(default="qwen/qwen3.8-27b", validation_alias="GROQ_VISION_MODEL")
    groq_timeout_seconds: float = Field(default=45.0, validation_alias="GROQ_TIMEOUT_SECONDS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
