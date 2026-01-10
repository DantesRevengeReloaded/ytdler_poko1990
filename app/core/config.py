from functools import lru_cache
from pathlib import Path
import os
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env explicitly
from dotenv import load_dotenv
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)


class Settings(BaseSettings):
    app_name: str = Field("PokoDL Web", env="POKODLER_APP_NAME")
    log_level: str = Field("INFO", env="POKODLER_LOG_LEVEL")
    download_dir: str = Field("downloads", env="POKODLER_DOWNLOAD_DIR")

    db_host: str = Field("localhost", env="POKODLER_DB_HOST")
    db_port: int = Field(5432, env="POKODLER_DB_PORT")
    db_name: str = Field("pokodler", env="POKODLER_DB_NAME")
    db_user: str = Field("pokodler", env="POKODLER_DB_USER")
    db_password: str = Field("", env="POKODLER_DB_PASSWORD")
    db_sslmode: str = Field("prefer", env="POKODLER_DB_SSLMODE")

    spotify_client_id: str = Field("", env="POKODLER_SPOTIFY_CLIENT_ID")
    spotify_client_secret: str = Field("", env="POKODLER_SPOTIFY_CLIENT_SECRET")

    model_config = SettingsConfigDict(env_prefix="POKODLER_", extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()


def db_dsn(settings: Settings | None = None) -> str:
    cfg = settings or get_settings()
    return (
        f"host={cfg.db_host} port={cfg.db_port} dbname={cfg.db_name} "
        f"user={cfg.db_user} password={cfg.db_password} sslmode={cfg.db_sslmode}"
    )
