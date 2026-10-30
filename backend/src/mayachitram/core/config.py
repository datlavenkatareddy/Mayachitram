from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="MAYACHITRAM_",
        env_file=".env",
        extra="ignore",
    )

    environment: str = "development"
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"]
    )
    max_upload_bytes: int = Field(default=20 * 1024 * 1024, validation_alias="MAX_UPLOAD_BYTES")
    max_image_pixels: int = Field(default=50_000_000, validation_alias="MAX_IMAGE_PIXELS")
    max_image_dimension: int = Field(default=8192, validation_alias="MAX_IMAGE_DIMENSION")

    data_dir: Path = Field(
        default_factory=lambda: Path.cwd() / "data",
        validation_alias="MAYACHITRAM_DATA_DIR",
    )
    database_filename: str = "mayachitram.db"

    groq_api_key: str | None = Field(default=None, validation_alias="GROQ_API_KEY")
    groq_vision_model: str = Field(
        default="llama-3.2-11b-vision-preview", validation_alias="GROQ_VISION_MODEL"
    )
    groq_chat_model: str = Field(
        default="llama-3.3-70b-versatile", validation_alias="GROQ_CHAT_MODEL"
    )
    groq_timeout_seconds: float = Field(default=45.0, validation_alias="GROQ_TIMEOUT_SECONDS")

    @property
    def database_path(self) -> Path:
        return self.data_dir / self.database_filename

    @property
    def storage_dir(self) -> Path:
        return self.data_dir / "storage"


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.storage_dir.mkdir(parents=True, exist_ok=True)
    return settings
