"""想看（订阅）列表业务：Web Session 与开放接口共用。"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap import BUILTIN_ADMIN_USERNAME
from app.models.media_subscription import MediaSubscription
from app.models.user import User
from app.schemas.media import MediaSubscriptionItem
from app.services.tmdb_client import fetch_media_detail, normalize_media_type, poster_url


def _truncate_overview(text: str, limit: int = 800) -> str:
    s = (text or "").strip()
    if len(s) <= limit:
        return s
    return s[:limit]


def subscription_to_item(row: MediaSubscription) -> MediaSubscriptionItem:
    return MediaSubscriptionItem(
        id=row.id,
        tmdb_id=row.tmdb_id,
        media_type=row.media_type,
        title=row.title,
        poster_path=row.poster_path or "",
        poster_url=poster_url(row.poster_path),
        overview=row.overview or "",
        release_date=row.release_date or "",
        created_at=row.created_at.isoformat() if row.created_at else "",
    )


async def get_builtin_admin_user(db: AsyncSession) -> User:
    """开放接口操作的想看列表归属内置 admin 账号。"""
    result = await db.execute(select(User).where(User.username == BUILTIN_ADMIN_USERNAME))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=500, detail="内置管理员账号不存在，请重启服务以完成初始化")
    return user


async def list_subscriptions_for_user(db: AsyncSession, user_id: int) -> list[MediaSubscriptionItem]:
    result = await db.execute(
        select(MediaSubscription)
        .where(MediaSubscription.user_id == user_id)
        .order_by(MediaSubscription.created_at.desc()),
    )
    rows = result.scalars().all()
    return [subscription_to_item(r) for r in rows]


async def add_subscription_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    media_type: str,
    tmdb_id: int,
) -> MediaSubscriptionItem:
    mt = normalize_media_type(media_type)
    existing = await db.execute(
        select(MediaSubscription).where(
            MediaSubscription.user_id == user_id,
            MediaSubscription.media_type == mt,
            MediaSubscription.tmdb_id == tmdb_id,
        ),
    )
    row = existing.scalar_one_or_none()
    if row is not None:
        return subscription_to_item(row)

    detail = await fetch_media_detail(db, mt, tmdb_id)
    row = MediaSubscription(
        user_id=user_id,
        tmdb_id=detail["tmdb_id"],
        media_type=mt,
        title=detail["title"],
        poster_path=detail.get("poster_path") or "",
        overview=_truncate_overview(detail.get("overview") or ""),
        release_date=detail.get("release_date") or "",
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return subscription_to_item(row)


async def remove_subscription_for_user(
    db: AsyncSession,
    user_id: int,
    *,
    media_type: str,
    tmdb_id: int,
) -> None:
    mt = normalize_media_type(media_type)
    result = await db.execute(
        select(MediaSubscription).where(
            MediaSubscription.user_id == user_id,
            MediaSubscription.media_type == mt,
            MediaSubscription.tmdb_id == tmdb_id,
        ),
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="未找到该想看记录")
    await db.delete(row)
    await db.commit()
