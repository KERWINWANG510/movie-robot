from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
engine = create_async_engine(
    settings.database_url,
    echo=False,
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session


async def init_db() -> None:
    import app.models  # noqa: F401 — 注册 ORM 模型元数据

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await _migrate_sqlite_schema()


async def _migrate_sqlite_schema() -> None:
    """为已存在的 SQLite 库补充新增列（create_all 不会改旧表结构）。"""
    url = get_settings().database_url
    if "sqlite" not in url:
        return
    from sqlalchemy import text

    async with engine.begin() as conn:
        r = await conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='system_config'"),
        )
        if r.scalar_one_or_none() is None:
            return
        r2 = await conn.execute(text("PRAGMA table_info(system_config)"))
        col_names = [row[1] for row in r2.fetchall()]
        if "rename_instruction" not in col_names:
            await conn.execute(
                text(
                    "ALTER TABLE system_config ADD COLUMN rename_instruction TEXT NOT NULL DEFAULT ''",
                ),
            )
