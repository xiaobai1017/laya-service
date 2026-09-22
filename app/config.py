from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LAYA_", env_file=".env", extra="ignore")

    api_key: str = ""
    model_mode: str = "router"
    default_model: str = "jev-latest"
    device: str | None = None
    preload: bool = True
    hf_token: str | None = None
    max_inflight: int = 2
    request_timeout_seconds: float = 60.0
    max_state_bytes: int = 262_144
    max_questions: int = 64
    max_choice_options: int = 32
    max_score_levels: int = 10
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()

