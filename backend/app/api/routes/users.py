from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.auth import PreferenceUpdate, UserPublic

router = APIRouter(prefix="/users", tags=["用户偏好"])


@router.patch("/me/preference", response_model=UserPublic)
async def update_preference(
    body: PreferenceUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UserPublic:
    user.auto_rename_without_preview = body.auto_rename_without_preview
    await db.commit()
    await db.refresh(user)
    return UserPublic.model_validate(user)
