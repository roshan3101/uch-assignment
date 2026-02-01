from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    api_base_url: str = Field(
        default="https://tender.nprocure.com",
        description="Base URL for the tender API"
    )
    api_timeout: int = Field(
        default=30,
        description="API request timeout in seconds",
        ge=5,
        le=120
    )

    rate_limit: float = Field(
        default=1.0,
        description="Delay between requests in seconds",
        ge=0.1,
        le=10.0
    )
    concurrency: int = Field(
        default=3,
        description="Number of concurrent browser instances",
        ge=1,
        le=10
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10
    )
    browser_headless: bool = Field(
        default=True,
        description="Run browser in headless mode"
    )
    timeout_seconds: int = Field(
        default=30,
        description="General timeout in seconds",
        ge=5,
        le=300
    )

    output_dir: Path = Field(
        default=Path("data/output"),
        description="Directory for output files"
    )
    metadata_dir: Path = Field(
        default=Path("data/metadata"),
        description="Directory for metadata files"
    )
    log_dir: Path = Field(
        default=Path("data/logs"),
        description="Directory for log files"
    )

    database_url: Optional[str] = Field(
        default=None,
        description="Database connection URL (postgresql://user:pass@host:port/db)"
    )
    use_database: bool = Field(
        default=False,
        description="Whether to use database storage"
    )

    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        description="User agent string for requests"
    )

    scraper_version: str = Field(
        default="1.0.0",
        description="Scraper version for metadata tracking"
    )

    @field_validator("output_dir", "metadata_dir", "log_dir")
    @classmethod
    def ensure_path_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    def get_output_path(self, filename: str) -> Path:
        return self.output_dir / filename

    def get_metadata_path(self, filename: str) -> Path:
        return self.metadata_dir / filename

    def get_log_path(self, filename: str) -> Path:
        return self.log_dir / filename


@lru_cache()
def get_settings() -> Settings:
    return Settings()
