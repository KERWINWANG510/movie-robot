"""从数据库 system_config 读取挂载与 AI 参数（不使用环境变量兜底）。"""

from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system_config import SystemConfig
from app.services.ai_providers import preset_base_url, resolve_effective_base_url


@dataclass
class AiCallParams:
    openai_base_url: str
    openai_api_key: str
    openai_model: str
    rename_instruction: str = ""


async def get_system_config_row(session: AsyncSession) -> SystemConfig | None:
    return await session.get(SystemConfig, 1)


def effective_mount_root(cfg: SystemConfig | None) -> Path:
    """仅从数据库读取挂载根路径；未配置则抛出 ValueError。"""
    if cfg is None:
        raise ValueError("系统配置不存在")
    raw = (cfg.mount_path or "").strip()
    if not raw:
        raise ValueError("未配置挂载根目录")
    return Path(raw).expanduser().resolve()


def effective_ai_params(cfg: SystemConfig | None) -> AiCallParams:
    """从数据库读取 AI 参数；预设服务商使用内置 Base URL。"""
    if cfg is None:
        return AiCallParams(openai_base_url="", openai_api_key="", openai_model="", rename_instruction="")
    pid = (getattr(cfg, "ai_provider", None) or "custom").strip() or "custom"
    base = resolve_effective_base_url(
        ai_provider=pid,
        stored_custom_url=(cfg.openai_base_url or ""),
    )
    return AiCallParams(
        openai_base_url=base,
        openai_api_key=(cfg.openai_api_key or "").strip(),
        openai_model=(cfg.openai_model or "").strip(),
        rename_instruction=(cfg.rename_instruction or "").strip(),
    )


def resolve_probe_base_url(
    *,
    body_ai_provider: str | None,
    body_openai_base_url: str | None,
    row: SystemConfig | None,
) -> str:
    """探测模型列表时解析 Base URL：请求体显式 URL 优先，其次未保存表单的 ai_provider，最后用库内配置。"""
    b = (body_openai_base_url or "").strip()
    if b:
        return b
    pid = (body_ai_provider or "").strip().lower()
    if pid and pid != "custom":
        u = preset_base_url(pid)
        if u:
            return u
    if row:
        return resolve_effective_base_url(
            ai_provider=(getattr(row, "ai_provider", None) or "custom"),
            stored_custom_url=(row.openai_base_url or ""),
        )
    return ""
