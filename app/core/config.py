from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    PROJECT_NAME: str = "Bulk Certificate Generator"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENV: str = "development"
    DEBUG: bool = True

    # Database configuration (defaults to SQLite WAL mode for zero-setup evaluation)
    DATABASE_URL: str = "sqlite+aiosqlite:///./certificates.db"

    # Certificate Storage Directory
    STORAGE_DIR: str = "./storage/certificates"

    # Batch and Concurrency Limits
    MAX_WORKER_THREADS: int = 4
    MAX_BATCH_RECIPIENTS: int = 5000

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def storage_path(self) -> Path:
        """Return resolved Path object for storage directory."""
        path = Path(self.STORAGE_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
