"""访问令牌管理与开放接口目录（需登录会话）。"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.api_access_token import ApiAccessToken
from app.models.user import User
from app.schemas.open_api import (
    ApiTokenCreatedResponse,
    ApiTokenCreateRequest,
    ApiTokenListResponse,
    ApiTokenPublic,
    OpenApiCatalogResponse,
)
from app.security.api_token import generate_api_token
from app.services.open_api_catalog import build_open_api_catalog

router = APIRouter(prefix="/settings", tags=["系统配置"])


def _is_expired(row: ApiAccessToken, now: datetime | None = None) -> bool:
    if row.expires_at is None:
        return False
    return row.expires_at <= (now or datetime.utcnow())


def _to_public(row: ApiAccessToken) -> ApiTokenPublic:
    return ApiTokenPublic(
        id=row.id,
        name=row.name,
        token_prefix=row.token_prefix,
        created_at=row.created_at,
        last_used_at=row.last_used_at,
        expires_at=row.expires_at,
        revoked_at=row.revoked_at,
        expired=_is_expired(row),
    )


@router.get("/api-tokens", response_model=ApiTokenListResponse)
async def list_api_tokens(
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ApiTokenListResponse:
    result = await db.execute(
        select(ApiAccessToken).order_by(ApiAccessToken.id.desc()),
    )
    rows = list(result.scalars().all())
    return ApiTokenListResponse(items=[_to_public(r) for r in rows])


@router.post("/api-tokens", response_model=ApiTokenCreatedResponse)
async def create_api_token(
    body: ApiTokenCreateRequest,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ApiTokenCreatedResponse:
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="请填写令牌名称")
    plain, prefix, digest = generate_api_token()
    now = datetime.utcnow()
    expires_at: datetime | None = None
    if body.expires_in_days is not None:
        expires_at = now + timedelta(days=body.expires_in_days)
    row = ApiAccessToken(
        name=name,
        token_prefix=prefix,
        token_hash=digest,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ApiTokenCreatedResponse(token=_to_public(row), plain_token=plain)


@router.delete("/api-tokens/{token_id}", response_model=ApiTokenPublic)
async def revoke_api_token(
    token_id: int,
    db: AsyncSession = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ApiTokenPublic:
    result = await db.execute(select(ApiAccessToken).where(ApiAccessToken.id == token_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="令牌不存在")
    if row.revoked_at is None:
        row.revoked_at = datetime.utcnow()
        await db.commit()
        await db.refresh(row)
    return _to_public(row)


@router.get("/open-api/catalog", response_model=OpenApiCatalogResponse)
async def open_api_catalog(
    _user: User = Depends(get_current_user),
) -> OpenApiCatalogResponse:
    return build_open_api_catalog()
