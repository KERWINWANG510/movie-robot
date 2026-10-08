from datetime import datetime

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.api_access_token import ApiAccessToken
from app.models.user import User
from app.security.api_token import extract_bearer_or_api_key, hash_api_token


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    session = request.session
    uid = session.get("user_id")
    if uid is None:
        raise HTTPException(status_code=401, detail="未登录或会话已过期")
    result = await db.execute(select(User).where(User.id == int(uid)))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_open_api_token(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-Api-Key"),
) -> ApiAccessToken:
    """校验开放接口 API Key，返回令牌记录。"""
    plain = extract_bearer_or_api_key(authorization, x_api_key)
    if not plain:
        raise HTTPException(status_code=401, detail="缺少 API Key（Authorization: Bearer 或 X-Api-Key）")
    digest = hash_api_token(plain)
    result = await db.execute(
        select(ApiAccessToken).where(
            ApiAccessToken.token_hash == digest,
            ApiAccessToken.revoked_at.is_(None),
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=401, detail="API Key 无效或已吊销")
    now = datetime.utcnow()
    if row.expires_at is not None and row.expires_at <= now:
        raise HTTPException(status_code=401, detail="API Key 已过期")
    row.last_used_at = now
    await db.commit()
    await db.refresh(row)
    return row
