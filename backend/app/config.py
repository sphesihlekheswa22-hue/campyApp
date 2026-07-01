from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://jse_user:jse_password@localhost:5432/jse_analytics"
    jwt_secret: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    upload_dir: str = "uploads"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@jse-analytics.com"
    app_env: str = "development"
    platform_owner_email: str = "admin@bluemachines.com"
    platform_owner_password: str = "Admin123!"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if isinstance(value, str) and value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql://", 1)
        return value


def resolve_database_url(url: str) -> str:
    """Ensure Neon/Render Postgres URLs include SSL when required."""
    if url.startswith("sqlite"):
        return url
    if "neon.tech" in url and "sslmode=" not in url:
        separator = "&" if "?" in url else "?"
        return f"{url}{separator}sslmode=require"
    return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
