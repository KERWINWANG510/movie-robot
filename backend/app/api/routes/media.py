from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.media_subscription import MediaSubscription
from app.models.user import User
from app.schemas.media import (
    MediaCardItem,
    MediaDetail,
    MediaListResponse,
    MediaSubscribeRequest,
    MediaSubscriptionItem,
    MediaSubscriptionListResponse,
)
from app.services.media_subscriptions import (
    add_subscription_for_user,
    list_subscriptions_for_user,
    remove_subscription_for_user,
)
from app.services.tmdb_client import (
    fetch_media_detail,
    fetch_now_playing_movies,
    fetch_on_the_air_tv,
    fetch_trending_all,
    normalize_media_type,
    search_media,
)

router = APIRouter(prefix="/media", tags=["影视"])


@router.get("/trending", response_model=MediaListResponse)
async def media_trending(
    page: int = Query(1, ge=1, le=500, description="页码"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MediaListResponse:
    """今日热门：同时包含电影与电视剧。"""
    data = await fetch_trending_all(db, page=page)
    return MediaListResponse(
        items=[MediaCardItem(**x) for x in data["items"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/movies/now-playing", response_model=MediaListResponse)
async def movies_now_playing(
    page: int = Query(1, ge=1, le=500, description="页码"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MediaListResponse:
    data = await fetch_now_playing_movies(db, page=page)
    return MediaListResponse(
        items=[MediaCardItem(**x) for x in data["items"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/tv/on-the-air", response_model=MediaListResponse)
async def tv_on_the_air(
    page: int = Query(1, ge=1, le=500, description="页码"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MediaListResponse:
    data = await fetch_on_the_air_tv(db, page=page)
    return MediaListResponse(
        items=[MediaCardItem(**x) for x in data["items"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/search", response_model=MediaListResponse)
async def media_search(
    q: str = Query(..., min_length=1, max_length=200, description="搜索关键词"),
    media_type: str = Query("all", description="媒体类型：all（电影+电视剧）、movie 或 tv"),
    page: int = Query(1, ge=1, le=500, description="页码"),
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> MediaListResponse:
    data = await search_media(db, query=q, media_type=media_type, page=page)
    return MediaListResponse(
        items=[MediaCardItem(**x) for x in data["items"]],
        page=data["page"],
        total_pages=data["total_pages"],
        total_results=data["total_results"],
    )


@router.get("/subscriptions", response_model=MediaSubscriptionListResponse)
async def list_subscriptions(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaSubscriptionListResponse:
    items = await list_subscriptions_for_user(db, user.id)
    return MediaSubscriptionListResponse(items=items)


@router.post("/subscriptions", response_model=MediaSubscriptionItem)
async def add_subscription(
    body: MediaSubscribeRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaSubscriptionItem:
    return await add_subscription_for_user(
        db,
        user.id,
        media_type=body.media_type,
        tmdb_id=body.tmdb_id,
    )


@router.delete("/subscriptions/{media_type}/{tmdb_id}")
async def remove_subscription(
    media_type: str,
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, bool]:
    await remove_subscription_for_user(
        db,
        user.id,
        media_type=media_type,
        tmdb_id=tmdb_id,
    )
    return {"ok": True}


@router.get("/{media_type}/{tmdb_id}", response_model=MediaDetail)
async def media_detail(
    media_type: str,
    tmdb_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> MediaDetail:
    mt = normalize_media_type(media_type)
    detail = await fetch_media_detail(db, mt, tmdb_id)
    sub = await db.execute(
        select(MediaSubscription.id).where(
            MediaSubscription.user_id == user.id,
            MediaSubscription.media_type == mt,
            MediaSubscription.tmdb_id == tmdb_id,
        ),
    )
    subscribed = sub.scalar_one_or_none() is not None
    return MediaDetail(**detail, subscribed=subscribed)
