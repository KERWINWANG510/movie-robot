from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "请在生产环境中修改-secret-key"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    session_cookie_name: str = "movie_robot_session"
    session_max_age: int = 60 * 60 * 24 * 7
    session_https_only: bool = False

    cors_origins: str = "http://localhost:5173"

    allow_registration: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
