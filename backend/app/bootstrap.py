"""应用启动时确保内置管理员与系统配置行存在（通过 ORM）。"""

from sqlalchemy import select

from app.database import async_session_factory
from app.models.system_config import SystemConfig
from app.models.user import User
from app.security.password import hash_password

BUILTIN_ADMIN_USERNAME = "admin"
BUILTIN_ADMIN_PASSWORD = "123456"


async def ensure_builtin_admin() -> None:
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == BUILTIN_ADMIN_USERNAME))
        if result.scalar_one_or_none() is not None:
            return
        session.add(
            User(
                username=BUILTIN_ADMIN_USERNAME,
                password_hash=hash_password(BUILTIN_ADMIN_PASSWORD),
                auto_rename_without_preview=False,
            )
        )
        await session.commit()


async def ensure_system_config() -> None:
    async with async_session_factory() as session:
        row = await session.get(SystemConfig, 1)
        if row is not None:
            return
        session.add(
            SystemConfig(
                id=1,
                mount_path="",
                ai_provider="custom",
                openai_base_url="",
                openai_api_key="",
                openai_model="",
                rename_instruction="",
            )
        )
        await session.commit()
