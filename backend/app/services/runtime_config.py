"""合并数据库 system_config 与环境变量默认值，供文件浏览与 AI 调用使用。"""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.models.system_config import SystemConfig


@dataclass
class AiCallParams:
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    rename_instruction: str = ""


async def get_system_config_row(session: AsyncSession) -> SystemConfig | None:
    return await session.get(SystemConfig, 1)


def effective_mount_root(cfg: SystemConfig | None, env: Settings | None = None) -> Path:
    env = env or get_settings()
    raw = ""
    if cfg is not None and (cfg.mount_path or "").strip():
        raw = (cfg.mount_path or "").strip()
    if not raw:
        raw = (env.mount_path or "").strip()
    return Path(raw).expanduser().resolve()


def effective_ai_params(cfg: SystemConfig | None, env: Settings | None = None) -> AiCallParams:
    env = env or get_settings()
    base = ""
    if cfg is not None and (cfg.openai_base_url or "").strip():
        base = (cfg.openai_base_url or "").strip()
    if not base:
        base = (env.openai_base_url or "").strip()
    key = ""
    if cfg is not None and (cfg.openai_api_key or "").strip():
        key = (cfg.openai_api_key or "").strip()
    if not key:
        key = (env.openai_api_key or "").strip()
    model = ""
    if cfg is not None and (cfg.openai_model or "").strip():
        model = (cfg.openai_model or "").strip()
    if not model:
        model = (env.openai_model or "").strip()
    ri = ""
    if cfg is not None and (cfg.rename_instruction or "").strip():
        ri = (cfg.rename_instruction or "").strip()
    if not ri:
        ri = (env.rename_instruction or "").strip()
    return AiCallParams(
        openai_base_url=base,
        openai_api_key=key,
        openai_model=model,
        rename_instruction=ri,
    )
