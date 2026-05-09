from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    secret_key: str = "请在生产环境中修改-secret-key"
    database_url: str = "sqlite+aiosqlite:///./data/app.db"
    # 容器内挂载的 NAS 目录根路径
    mount_path: str = "/data"
    session_cookie_name: str = "movie_robot_session"
    session_max_age: int = 60 * 60 * 24 * 7
    # 置于 HTTPS 反代后时可设为 True，强制 Cookie 仅通过 HTTPS 传递
    session_https_only: bool = False

    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    cors_origins: str = "http://localhost:5173"

    # 是否允许开放注册（生产建议关闭，仅首次部署创建账号时可开启）
    allow_registration: bool = False

    @property
    def mount_root(self) -> Path:
        return Path(self.mount_path).resolve()

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
